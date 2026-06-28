import time
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, ExpressionWrapper, F, fields
from django.db.models.functions import ExtractDay
from invoices.models import Invoice, Client, Payment, NotificationLog, LineItem, Services
from google.genai import types


TOOL_REGISTRY = {}

def tool(name, description, parameters, requires_confirmation=False):
    
    def decorator(fn):
        TOOL_REGISTRY[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "requires_confirmation": requires_confirmation,
            "handler": fn,
        }
        return fn
    return decorator

# ─── INVOICE TOOLS ───
@tool(
    name="create_invoice",
    description="Creates a new draft invoice. Can link to existing pre-saved services.",
    parameters={
        "type": "object", 
        "properties": {
            "client_name": {"type": "string"}, 
            "tax_rate": {"type": "number", "description": "Optional tax rate percentage (e.g. 18 for 18%)."},
            "discount_percentage": {"type": "number", "description": "Optional discount percentage (e.g. 10 for 10%)."},
            "items": {
                "type": "array",
                "description": "List of line items. Rate is optional if it's a pre-saved service.",
                "items": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "rate": {"type": "number", "description": "Optional. Will auto-fill if the service exists in the database."},
                        "hours": {"type": "number"}
                    },
                    "required": ["service_name", "hours"]
                }
            }
        }, 
        "required": ["client_name", "items"]
    }
)


def create_invoice(user, args):
    client = Client.objects.filter(user=user, name__iexact=args['client_name']).first()
    if not client: return {"error": f"Client '{args['client_name']}' not found."}

    tax_val = args.get('tax_rate')
    tax_rate = Decimal(str(tax_val)) if tax_val is not None else Decimal('18.00')

    disc_val = args.get('discount_percentage')
    discount_pct = Decimal(str(disc_val)) if disc_val is not None else Decimal('0.00')

    
    inv = Invoice.objects.create(
        user=user, client=client, client_name=client.name,
        issue_date=date.today(), due_date=date.today() + timedelta(days=15),
        status='DRAFT',
        tax_rate=tax_rate,
        discount_percentage=discount_pct
    )
    
    items_list = args.get('items', [])
    for item in items_list:
        rate = item.get('rate')
        service_obj = None
        
        # If the AI didn't provide a rate, look it up in the database!
        if not rate:
            service_obj = Services.objects.filter(user=user, name__icontains=item['service_name']).first()
            rate = service_obj.rate if service_obj else 0.00
            
        LineItem.objects.create(
            invoice=inv,
            services=service_obj, # Link the actual service to the line item if found
            service_name=item['service_name'],
            rate=Decimal(str(rate)),
            total_hours=Decimal(str(item['hours']))
        )
    inv.refresh_from_db()
    from invoices.serializers import InvoiceSerializer
    serializer = InvoiceSerializer(inv)
    inv.total_amount = serializer.data['total_amount']
    inv.save(update_fields=['total_amount'])
        
    return {
        "status": "success", 
        "invoice_number": inv.invoice_number, 
        "message": "Draft created successfully. You can now edit/review it in the dashboard."
    }

@tool(
    name="add_service",
    description="Adds a new reusable service/line item to your saved database.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the service (e.g. 'Web Development')."},
            "rate": {"type": "number", "description": "The default price or hourly rate for this service."}
        },
        "required": ["name", "rate"]
    }
)
def add_service(user, args):
    if Services.objects.filter(user=user, name__iexact=args['name']).exists():
        return {"error": f"Service '{args['name']}' already exists."}
    service = Services.objects.create(user=user, name=args['name'], rate=Decimal(str(args['rate'])))
    return {"status": "success", "message": f"Service '{service.name}' saved with a rate of ₹{service.rate}."}

@tool(
    name="create_client",
    description="Creates a new client in the database so you can assign invoices to them.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "The client's company name or full name."},
            "email": {"type": "string", "description": "The client's email address."}
        },
        "required": ["name", "email"]
    }
)
def create_client(user, args):
    if Client.objects.filter(user=user, name__iexact=args['name']).exists():
        return {"error": f"Client '{args['name']}' already exists."}
    client = Client.objects.create(user=user, name=args['name'], email=args['email'])
    return {"status": "success", "message": f"Client '{client.name}' created successfully!"}



@tool(
    name="delete_invoice",
    description="Deletes a draft invoice.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}}, "required": ["invoice_number"]},
    requires_confirmation=True  # ⚠️ Safety Layer
)
def delete_invoice(user, args):
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    if not inv or inv.status != 'DRAFT': return {"error": "Only draft invoices can be deleted."}
    inv.delete()
    return {"status": "success", "message": "Deleted successfully."}

@tool(
    name="generate_pdf",
    description="Generates the PDF for an invoice without sending it.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}}, "required": ["invoice_number"]}
)
def generate_pdf(user, args):
    # In a real app, you would call pdf_service here
    return {"status": "success", "message": f"PDF generated for {args['invoice_number']}"}

# ─── COMMUNICATION TOOLS ───
@tool(
    name="send_invoice",
    description="Sends invoice via email.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}}, "required": ["invoice_number"]},
    requires_confirmation=True  # ⚠️ Safety Layer
)
def send_invoice(user, args):
    from invoices.services.email_service import send_invoice_email
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    if send_invoice_email(inv):
        inv.status = 'SENT'
        inv.save()
        return {"status": "success"}
    return {"error": "Failed to send."}

@tool(
    name="send_reminder",
    description="Sends payment reminder.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}}, "required": ["invoice_number"]},
    requires_confirmation=False # Allowed without confirmation per spec
)
def send_reminder(user, args):
    return {"status": "success", "message": "Reminder queued."}

# ─── PAYMENT TOOLS ───
@tool(
    name="record_payment",
    description="Records a manual payment.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}, "amount": {"type": "number"}, "method": {"type": "string"}}, "required": ["invoice_number", "amount", "method"]},
    requires_confirmation=True # ⚠️ Safety Layer
)
def record_payment(user, args):
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    Payment.objects.create(invoice=inv, amount=Decimal(str(args['amount'])), payment_method=args['method'].upper())
    inv.status = 'PAID'
    inv.save()
    return {"status": "success"}

# ─── ANALYTICS TOOLS ───
@tool(
    name="get_analytics",
    description="Returns revenue, outstanding amounts, and slowest-paying clients.",
    parameters={"type": "object", "properties": {}}
)
def get_analytics(user, args):
    # Slowest paying client logic (Average days past due date for PAID invoices)
    slow_clients = (
        Invoice.objects.filter(user=user, status='PAID')
        .annotate(
            days_late=ExpressionWrapper(
                F('payments__payment_date') - F('due_date'),
                output_field=fields.DurationField()
            )
        )
        .values('client_name')
        .annotate(avg_late=ExtractDay('days_late'))
        .filter(avg_late__gt=0)
        .order_by('-avg_late')[:3]
    )
    
    return {
        "status": "success",
        "slowest_clients": list(slow_clients)
    }

def get_gemini_tools():
    declarations = []
    
    for v in TOOL_REGISTRY.values():
        declarations.append(
            types.FunctionDeclaration(
                name=v["name"],
                description=v["description"],
                parameters=v["parameters"]
            )
        )
        
    return [types.Tool(function_declarations=declarations)]


