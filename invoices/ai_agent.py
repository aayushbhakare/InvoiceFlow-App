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
    if pending_action_id:
        return _handle_pending_action(user, pending_action_id)
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
        system_instruction="""\
You are InvoiceFlow AI, a highly capable financial and business assistant. Your purpose is to help the user manage their invoicing, clients, services, and business analytics seamlessly.
You have full access to a suite of backend tools. You can:
1. INVOICING: Create, edit, search, delete, and bulk-generate PDFs for invoices.
2. DATABASE MANAGEMENT: Create, edit, and search clients and services.
3. COMMUNICATION: Send invoices (with PDF) and payment reminders via email. You can bulk send drafts or reminders based on filters.
4. PAYMENTS: Record manual payments to mark invoices as PAID (either single or in bulk). **IMPORTANT:** Only online payment methods are supported (UPI, NEFT, RAZORPAY). CASH is NOT allowed.
5. ANALYTICS: Generate business analytics (slowest-paying clients, revenue, etc.).
CRITICAL RULE #1 — ASK BEFORE YOU ACT:
If the user's request is MISSING any required information for a tool, you MUST stop and ask a clear follow-up question. NEVER guess, fabricate, or use placeholder values.
Examples:
- User: "Create an invoice" -> ASK: "Sure! Which client is this for, and what services/line items should I include?"
- User: "Create an invoice for TechCorp" -> ASK: "Got it. What services and hours should I add as line items?"
- User: "Add a new client" -> ASK: "What is the client's name and email address?"
- User: "Add a service" -> ASK: "What is the service name and its rate?"
- User: "Send the invoice" -> Use search_invoices to find recent invoices, then ASK which one to send.
- User: "Record a payment for INV-2026-07-0001" -> ASK: "How much was the payment, and what was the method (UPI, NEFT, Razorpay)?"
CRITICAL RULE #2 — USE SEARCH TOOLS FIRST:
When the user refers to data that might exist (clients, invoices, services), ALWAYS use the appropriate search tool first to verify it exists before acting. Never assume a record exists.
Examples:
- User: "What invoices does Acme have?" -> Call search_invoices(client_name="Acme") first.
- User: "Update TechCorp's email" -> Call search_clients(query="TechCorp") first to confirm the client exists.
- User: "Delete the draft invoice" -> Call search_invoices(status="DRAFT") to find which drafts exist, then confirm.
CRITICAL RULE #3 — BULK OPERATIONS AND CHAINING:
You CAN chain multiple tools in a single conversation turn. If the user asks for bulk operations (like "send all drafts", "remind all overdue clients", "mark all TechCorp invoices as paid"), use your powerful bulk tools (`bulk_send_invoices`, `bulk_send_reminders`, `bulk_record_payments`, `bulk_generate_pdfs`).
Example: "Create a client named John at john@test.com, add a Web Dev service at 2000, and create an invoice for John with 10 hours of Web Dev"
-> Step 1: create_client -> Step 2: add_service -> Step 3: create_invoice
CRITICAL RULE #4 — TONE AND FORMAT:
- Be concise, professional, and friendly.
- When showing search results, format them clearly with invoice numbers, amounts, and statuses.
- After completing an action, give a brief confirmation.
- Never hallucinate data. If a tool returns an error, relay it honestly.""",
        tools=get_gemini_tools()
        ),
        history=history
    )
    try:
        response = chat.send_message(user_message or "Continue")
    except Exception as e:
        return {"error": str(e)}
    tool_steps = []
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
        if tool_meta['requires_confirmation']:
            pending = PendingAction.objects.create(
                user=user,
                tool_name=fn_name,
                tool_args=fn_args,
                expires_at=timezone.now() + timedelta(minutes=10)
            )
            args_summary = ', '.join(f"{k}={v}" for k, v in fn_args.items()) if fn_args else 'no arguments'
            return {
                "requires_confirmation": True,
                "pending_action_id": str(pending.id),
                "message": f"I need your approval to run **{fn_name}** ({args_summary}).",
                "tool_steps": tool_steps
            }
        start_time = time.time()
        result = tool_meta['handler'](user, fn_args)
        duration_ms = int((time.time() - start_time) * 1000)
        AIAuditLog.objects.create(
            user=user, tool_name=fn_name, tool_args=fn_args,
            required_confirmation=False, status=result.get('status', 'failed'),
            result=result, duration_ms=duration_ms
        )
        tool_steps.append({"tool": fn_name, "status": "completed"})
        response = chat.send_message([
            types.Part.from_function_response(name=fn_name, response=result)
        ])
    ai_text = response.text if hasattr(response, 'text') else "Done."
    ChatMessage.objects.create(user=user, role='model', content=ai_text)
    return {"response": ai_text, "requires_confirmation": False, "tool_steps": tool_steps}
def _handle_pending_action(user, pending_action_id):
    with transaction.atomic():
        try:
            pending = PendingAction.objects.select_for_update(nowait=True).get(id=pending_action_id, user=user)
        except PendingAction.DoesNotExist:
            return {"error": "Action not found or already processed."}
        if pending.status != 'pending':
            return {"error": f"Action is already {pending.status}."}
        if timezone.now() > pending.expires_at:
            pending.status = 'expired'
            pending.save()
            return {"error": "Action request has expired (10 min timeout)."}
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
        return process_chat_message(
            user, 
            user_message=f"SYSTEM: The user approved {pending.tool_name}. Result: {json.dumps(result)}"
        )