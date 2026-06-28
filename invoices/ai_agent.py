import json
import time
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from google import genai
from google.genai import types
from invoices.models import ChatMessage, PendingAction, AIAuditLog
from .ai_tools import TOOL_REGISTRY, get_gemini_tools

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def process_chat_message(user, user_message=None, pending_action_id=None):
    
    # 1. Handle Pending Action Confirmation (Concurrency Safe)
    if pending_action_id:
        return _handle_pending_action(user, pending_action_id)

    # 2. Standard Chat Flow
    ChatMessage.cleanup_old_messages(user)
    if user_message:
        ChatMessage.objects.create(user=user, role='user', content=user_message)

    history = []
    for msg in ChatMessage.objects.filter(user=user).order_by('created_at'):
        history.append(types.Content(
            role=msg.role,
            parts=[types.Part.from_text(text=msg.content or json.dumps(msg.tool_calls))]
        ))
    chat = client.chats.create(
        model="gemini-3.5-flash",
        config=types.GenerateContentConfig(
        system_instruction="""You are InvoiceFlow AI, a highly capable financial and business assistant. Your purpose is to help the user manage their invoicing, clients, 
                            services, and business analytics seamlessly.
                            You have full access to a suite of backend tools. You can:
                            1. INVOICING: Create and delete draft invoices, attach custom line items, and apply dynamic tax rates and discounts.
                            2. DATABASE MANAGEMENT: Create new clients and add new reusable services directly to the database.
                            3. COMMUNICATION: Send invoices (with PDF attachments) and payment reminders to clients via email.
                            4. PAYMENTS: Record manual payments to mark invoices as PAID.
                            5. ANALYTICS: Generate business analytics, such as identifying the slowest-paying clients.

                            CRITICAL RULES:
                            - Autonomy: Always use the provided tools to fulfill the user's requests. Never hallucinate data if a tool can fetch it.
                            - Missing Information: If the user asks to create a client, service, or invoice, check the tool's required parameters. 
                              If the user's prompt is missing required fields (like an email address for a new client, or a rate for a new service), 
                              you MUST stop and politely ask them for the missing information BEFORE calling the tool.
                            - Tone: Be concise, professional, and friendly.""",
        tools=get_gemini_tools()
        ),
        history=history
    )

    try:
        response = chat.send_message(user_message or "Continue")
    except Exception as e:
        return {"error": str(e)}

    tool_steps = []
    
    # 3. Tool Orchestration Loop (Max 8 turns)
    for _ in range(8):
        
       
        if response.function_calls:
            fn = response.function_calls[0]
            fn_name = fn.name
            fn_args = fn.args if fn.args else {}
        else:
            break 

        tool_meta = TOOL_REGISTRY.get(fn_name)

        if not tool_meta:
            response = chat.send_message(f"Error: Tool {fn_name} not found.")
            continue

        # 4. SAFETY GATE: Requires Confirmation
        if tool_meta['requires_confirmation']:
            # Create pending action expiring in 10 minutes
            pending = PendingAction.objects.create(
                user=user,
                tool_name=fn_name,
                tool_args=fn_args,
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            return {
                "requires_confirmation": True,
                "pending_action_id": str(pending.id),
                "message": f"Action '{fn_name}' requires your approval to proceed.",
                "tool_steps": tool_steps
            }

        # 5. SAFE TOOL EXECUTION
        start_time = time.time()
        result = tool_meta['handler'](user, fn_args)
        duration_ms = int((time.time() - start_time) * 1000)

        # Write Audit Log
        AIAuditLog.objects.create(
            user=user, tool_name=fn_name, tool_args=fn_args,
            required_confirmation=False, status=result.get('status', 'failed'),
            result=result, duration_ms=duration_ms
        )

        tool_steps.append({"tool": fn_name, "status": "completed"})
        
        # Feed the result back to AI using the proper Part function response
        response = chat.send_message([
            types.Part.from_function_response(name=fn_name, response=result)
        ])




    ai_text = response.text if hasattr(response, 'text') else "Done."
    ChatMessage.objects.create(user=user, role='model', content=ai_text)

    return {"response": ai_text, "requires_confirmation": False, "tool_steps": tool_steps}


def _handle_pending_action(user, pending_action_id):
    
    with transaction.atomic():
        try:
            # Lock the row to prevent race conditions
            pending = PendingAction.objects.select_for_update(nowait=True).get(id=pending_action_id, user=user)
        except PendingAction.DoesNotExist:
            return {"error": "Action not found or already processed."}

        if pending.status != 'pending':
            return {"error": f"Action is already {pending.status}."}
            
        if timezone.now() > pending.expires_at:
            pending.status = 'expired'
            pending.save()
            return {"error": "Action request has expired (10 min timeout)."}

        # Mark as approved and execute
        pending.status = 'approved'
        pending.save()

        tool_meta = TOOL_REGISTRY.get(pending.tool_name)
        start_time = time.time()
        result = tool_meta['handler'](user, pending.tool_args)
        duration_ms = int((time.time() - start_time) * 1000)

        AIAuditLog.objects.create(
            user=user, tool_name=pending.tool_name, tool_args=pending.tool_args,
            required_confirmation=True, status=result.get('status', 'failed'),
            result=result, duration_ms=duration_ms
        )

        # Resume the conversation loop by telling the LLM the tool was approved
        return process_chat_message(
            user, 
            user_message=f"SYSTEM: The user approved {pending.tool_name}. Result: {json.dumps(result)}"
        )
