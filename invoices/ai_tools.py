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
        if not rate:
            service_obj = Services.objects.filter(user=user, name__icontains=item['service_name']).first()
            rate = service_obj.rate if service_obj else 0.00
        LineItem.objects.create(
            invoice=inv,
            services=service_obj, 
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
    requires_confirmation=True  
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
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    if not inv:
        return {"error": f"Invoice '{args['invoice_number']}' not found."}
    try:
        from invoices.services.pdf_service import generate_invoice_pdf
        generate_invoice_pdf(inv)
        return {"status": "success", "message": f"PDF generated for {inv.invoice_number}. You can download it from the dashboard."}
    except Exception as e:
        return {"error": f"PDF generation failed: {str(e)}"}
@tool(
    name="send_invoice",
    description="Sends invoice via email.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}}, "required": ["invoice_number"]},
    requires_confirmation=True  
)
def send_invoice(user, args):
    from invoices.services.email_service import send_invoice_email
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    if not inv:
        return {"error": f"Invoice '{args['invoice_number']}' not found."}
    if send_invoice_email(inv):
        inv.status = 'SENT'
        inv.save()
        return {"status": "success"}
    return {"error": "Failed to send."}
@tool(
    name="send_reminder",
    description="Sends payment reminder.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}}, "required": ["invoice_number"]},
    requires_confirmation=False 
)
def send_reminder(user, args):
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    if not inv:
        return {"error": f"Invoice '{args['invoice_number']}' not found."}
    if inv.status not in ('SENT', 'OVERDUE'):
        return {"error": f"Cannot send reminder for a {inv.status.lower()} invoice. Invoice must be sent or overdue."}
    if not inv.client or not inv.client.email:
        return {"error": "Client does not have an email address."}
    from invoices.services.email_service import send_reminder_email
    from invoices.services.whatsapp_service import send_whatsapp_reminder
    success_email = send_reminder_email(inv, 'REMINDER_ON_DUE')
    success_wa = send_whatsapp_reminder(inv, 'REMINDER_ON_DUE')
    if success_email or success_wa:
        msg = f"Payment reminder sent to {inv.client.email}"
        if success_wa:
            msg += f" and WhatsApp ({inv.client.phone})"
        return {"status": "success", "message": f"{msg}."}
    return {"error": "Failed to send reminder. Check notification logs for details."}
@tool(
    name="record_payment",
    description="Records a manual payment.",
    parameters={"type": "object", "properties": {"invoice_number": {"type": "string"}, "amount": {"type": "number"}, "method": {"type": "string"}}, "required": ["invoice_number", "amount", "method"]},
    requires_confirmation=True 
)
def record_payment(user, args):
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    if not inv:
        return {"error": f"Invoice '{args['invoice_number']}' not found."}
    if inv.status == 'PAID':
        return {"error": "Invoice is already marked as paid."}
    if inv.status == 'CANCELLED':
        return {"error": "Cannot record payment for a cancelled invoice."}
    payment_amount = Decimal(str(args['amount']))
    Payment.objects.create(invoice=inv, amount=payment_amount, payment_method=args['method'].upper())
    total_paid = sum(p.amount for p in inv.payments.all())
    if total_paid >= inv.total_amount:
        inv.status = 'PAID'
    inv.save()
    return {"status": "success", "message": f"Payment of ₹{payment_amount} recorded."}
@tool(
    name="get_analytics",
    description="Returns revenue, outstanding amounts, and slowest-paying clients.",
    parameters={"type": "object", "properties": {}}
)
def get_analytics(user, args):
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
@tool(
    name="search_invoices",
    description="Search invoices by client name, status, or invoice number. Returns a summary list of matching invoices (max 20).",
    parameters={
        "type": "object",
        "properties": {
            "client_name": {"type": "string", "description": "Optional. Filter by client name (partial match)."},
            "status": {"type": "string", "description": "Optional. Filter by status: DRAFT, SENT, PAID, OVERDUE, CANCELLED."},
            "invoice_number": {"type": "string", "description": "Optional. Filter by invoice number (partial match)."}
        }
    }
)
def search_invoices(user, args):
    qs = Invoice.objects.filter(user=user)
    if args.get('client_name'):
        qs = qs.filter(client_name__icontains=args['client_name'])
    if args.get('status'):
        qs = qs.filter(status__iexact=args['status'])
    if args.get('invoice_number'):
        qs = qs.filter(invoice_number__icontains=args['invoice_number'])
    results = list(qs.order_by('-issue_date')[:20].values(
        'invoice_number', 'client_name', 'total_amount', 'status', 'issue_date', 'due_date'
    ))
    for r in results:
        r['total_amount'] = str(r['total_amount'])
        r['issue_date'] = str(r['issue_date']) if r['issue_date'] else None
        r['due_date'] = str(r['due_date']) if r['due_date'] else None
    if not results:
        return {"status": "success", "message": "No invoices found matching your criteria.", "results": []}
    return {"status": "success", "count": len(results), "results": results}
@tool(
    name="search_clients",
    description="Search clients by name or email. Leave query empty to list all clients. Returns matching clients with their invoice count and total billed.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional. Search term to match against client name or email."}
        }
    }
)
def search_clients(user, args):
    query = args.get('query', '')
    from django.db.models import Q
    qs = Client.objects.filter(user=user)
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(email__icontains=query))
    qs = qs.annotate(
        invoice_count=Count('invoices'),
        total_billed=Sum('invoices__total_amount')
    )
    results = []
    for c in qs[:20]:
        results.append({
            "name": c.name,
            "email": c.email or "N/A",
            "phone": c.phone or "N/A",
            "status": "active" if c.is_active else "inactive",
            "invoice_count": c.invoice_count,
            "total_billed": str(c.total_billed or 0),
        })
    if not results:
        return {"status": "success", "message": "No clients found." if not query else f"No clients found matching '{query}'.", "results": []}
    return {"status": "success", "count": len(results), "results": results}
@tool(
    name="search_services",
    description="Search saved services/line items by name. Leave query empty to list all services. Returns matching services with their rates.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional. Search term to match against service name."}
        }
    }
)
def search_services(user, args):
    query = args.get('query', '')
    qs = Services.objects.filter(user=user)
    if query:
        qs = qs.filter(name__icontains=query)
    results = list(qs[:20].values('id', 'name', 'description', 'rate'))
    for r in results:
        r['rate'] = str(r['rate'])
    if not results:
        return {"status": "success", "message": "No services found." if not query else f"No services found matching '{query}'.", "results": []}
    return {"status": "success", "count": len(results), "results": results}
@tool(
    name="update_client",
    description="Update an existing client's details. Use search_clients first to verify the client exists.",
    parameters={
        "type": "object",
        "properties": {
            "client_name": {"type": "string", "description": "Current name of the client to update."},
            "new_name": {"type": "string", "description": "Optional. New name for the client."},
            "email": {"type": "string", "description": "Optional. New email address."},
            "phone": {"type": "string", "description": "Optional. New phone number."},
            "address": {"type": "string", "description": "Optional. New address."},
            "is_active": {"type": "boolean", "description": "Optional. Mark the client as active (true) or inactive (false)."}
        },
        "required": ["client_name"]
    },
    requires_confirmation=True
)
def update_client(user, args):
    client_obj = Client.objects.filter(user=user, name__iexact=args['client_name']).first()
    if not client_obj:
        return {"error": f"Client '{args['client_name']}' not found."}
    updated = []
    if args.get('new_name'):
        client_obj.name = args['new_name']
        updated.append(f"name -> {args['new_name']}")
    if args.get('email'):
        client_obj.email = args['email']
        updated.append(f"email -> {args['email']}")
    if args.get('phone'):
        client_obj.phone = args['phone']
        updated.append(f"phone -> {args['phone']}")
    if args.get('address'):
        client_obj.address = args['address']
        updated.append(f"address -> {args['address']}")
    if 'is_active' in args:
        client_obj.is_active = args['is_active']
        status_text = "Active" if args['is_active'] else "Inactive"
        updated.append(f"status -> {status_text}")
    if not updated:
        return {"error": "No fields to update were provided."}
    client_obj.save()
    return {"status": "success", "message": f"Client updated: {', '.join(updated)}"}
@tool(
    name="update_invoice",
    description="Update an existing invoice's metadata (status, due date, discount, tax rate, notes).",
    parameters={
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string", "description": "The invoice number to update."},
            "status": {"type": "string", "description": "Optional. New status: DRAFT, SENT, PAID, OVERDUE, CANCELLED."},
            "due_date": {"type": "string", "description": "Optional. New due date in YYYY-MM-DD format."},
            "discount_percentage": {"type": "number", "description": "Optional. New discount percentage."},
            "tax_rate": {"type": "number", "description": "Optional. New tax rate percentage."},
            "notes": {"type": "string", "description": "Optional. Notes to add to the invoice."}
        },
        "required": ["invoice_number"]
    },
    requires_confirmation=True
)
def update_invoice(user, args):
    inv = Invoice.objects.filter(user=user, invoice_number=args['invoice_number']).first()
    if not inv:
        return {"error": f"Invoice '{args['invoice_number']}' not found."}
    updated = []
    if args.get('status'):
        new_status = args['status'].upper()
        if inv.status in ['PAID', 'CANCELLED'] and new_status != inv.status:
            return {"error": f"Cannot change status of a {inv.status} invoice."}
        if new_status == 'DRAFT' and inv.status in ['SENT', 'OVERDUE']:
            return {"error": f"Cannot revert a {inv.status} invoice back to DRAFT."}
        inv.status = new_status
        updated.append(f"status -> {inv.status}")
    if args.get('due_date'):
        from datetime import datetime
        inv.due_date = datetime.strptime(args['due_date'], '%Y-%m-%d').date()
        updated.append(f"due_date -> {args['due_date']}")
    if args.get('discount_percentage') is not None:
        inv.discount_percentage = Decimal(str(args['discount_percentage']))
        updated.append(f"discount -> {args['discount_percentage']}%")
    if args.get('tax_rate') is not None:
        inv.tax_rate = Decimal(str(args['tax_rate']))
        updated.append(f"tax_rate -> {args['tax_rate']}%")
    if args.get('notes'):
        inv.notes = args['notes']
        updated.append("notes updated")
    if not updated:
        return {"error": "No fields to update were provided."}
    inv.save()
    return {"status": "success", "message": f"Invoice {inv.invoice_number} updated: {', '.join(updated)}"}
@tool(
    name="update_service",
    description="Update an existing service's name, rate, or description.",
    parameters={
        "type": "object",
        "properties": {
            "service_name": {"type": "string", "description": "Current name of the service to update."},
            "new_name": {"type": "string", "description": "Optional. New name for the service."},
            "rate": {"type": "number", "description": "Optional. New rate."},
            "description": {"type": "string", "description": "Optional. New description."}
        },
        "required": ["service_name"]
    },
    requires_confirmation=True
)
def update_service(user, args):
    svc = Services.objects.filter(user=user, name__iexact=args['service_name']).first()
    if not svc:
        return {"error": f"Service '{args['service_name']}' not found."}
    updated = []
    if args.get('new_name'):
        svc.name = args['new_name']
        updated.append(f"name -> {args['new_name']}")
    if args.get('rate') is not None:
        svc.rate = Decimal(str(args['rate']))
        updated.append(f"rate -> ₹{args['rate']}")
    if args.get('description'):
        svc.description = args['description']
        updated.append("description updated")
    if not updated:
        return {"error": "No fields to update were provided."}
    svc.save()
    return {"status": "success", "message": f"Service updated: {', '.join(updated)}"}
@tool(
    name="bulk_send_invoices",
    description="Sends invoices in bulk based on filters. Groups them into batches of 5 per email to respect SMTP limits. Always confirm before sending.",
    parameters={
        "type": "object",
        "properties": {
            "client_name": {"type": "string", "description": "Optional. Only send invoices for this client."},
            "status_filter": {"type": "string", "description": "Optional. Filter by status (e.g. DRAFT). Default is DRAFT, SENT, OVERDUE."},
            "month": {"type": "integer", "description": "Optional. Filter by issue month (1-12)."},
            "override_email": {"type": "string", "description": "Optional. Send to this email instead of the client's saved email."}
        }
    },
    requires_confirmation=True
)
def bulk_send_invoices(user, args):
    from invoices.services.email_service import send_invoice_email
    from invoices.services.pdf_service import generate_invoice_pdf
    import logging
    logger = logging.getLogger(__name__)
    qs = Invoice.objects.filter(user=user)
    if args.get('status_filter'):
        qs = qs.filter(status__iexact=args['status_filter'])
    else:
        qs = qs.filter(status__in=['DRAFT', 'SENT', 'OVERDUE'])
    if args.get('month'):
        qs = qs.filter(issue_date__month=args['month'])
    client_obj = None
    if args.get('client_name'):
        client_obj = Client.objects.filter(user=user, name__icontains=args['client_name']).first()
        if not client_obj:
            return {"error": f"Client '{args['client_name']}' not found."}
        qs = qs.filter(client=client_obj)
    invoices = list(qs.order_by('client_id', 'issue_date'))
    if not invoices:
        return {"error": "No invoices found matching criteria."}
    from collections import defaultdict
    client_invoices = defaultdict(list)
    for inv in invoices:
        if inv.client:
            client_invoices[inv.client].append(inv)
    total_sent = 0
    errors = []
    batches_sent = 0
    for client, invs in client_invoices.items():
        target_email = args.get('override_email') or client.email
        if not target_email:
            errors.append(f"Skipped {client.name} - no email.")
            continue
        BATCH_SIZE = 5
        batches = [invs[i:i+BATCH_SIZE] for i in range(0, len(invs), BATCH_SIZE)]
        for batch_idx, batch in enumerate(batches):
            try:
                from django.core.mail import EmailMessage as DjangoEmail
                from django.conf import settings as django_settings
                profile = getattr(user, 'profile', None)
                sender_name = getattr(profile, 'display_name', '') or user.email
                from_email = f"{sender_name} via InvoiceFlow <{django_settings.DEFAULT_FROM_EMAIL}>"
                inv_numbers = [inv.invoice_number for inv in batch]
                subject = f"Invoices from {sender_name}: {', '.join(inv_numbers)}"
                body = f"<p>Hi {client.contact_person or client.name},</p>"
                body += f"<p>Please find attached {len(batch)} invoice(s):</p><ul>"
                for inv in batch:
                    body += f"<li>{inv.invoice_number} — ₹{inv.total_amount}</li>"
                body += "</ul><p>Thank you for your business!</p>"
                email = DjangoEmail(
                    subject=subject, body=body, from_email=from_email,
                    to=[target_email], reply_to=[user.email],
                )
                email.content_subtype = 'html'
                for inv in batch:
                    try:
                        pdf_bytes = generate_invoice_pdf(inv)
                        email.attach(f"invoice_{inv.invoice_number}.pdf", pdf_bytes, 'application/pdf')
                    except Exception as e:
                        errors.append(f"{inv.invoice_number}: PDF failed - {str(e)}")
                        continue
                email.send(fail_silently=False)
                for inv in batch:
                    inv.status = 'SENT'
                    inv.save(update_fields=['status'])
                    NotificationLog.objects.create(
                        invoice=inv, event_type='INVOICE_SENT',
                        delivery_status='SUCCESS', recipient_email=target_email,
                        metadata={'bulk_send': True, 'batch': batch_idx + 1}
                    )
                total_sent += len(batch)
                batches_sent += 1
            except Exception as e:
                logger.error(f"Bulk send failed for {client.name}: {e}")
                errors.append(f"{client.name} batch failed: {str(e)}")
    summary = f"Sent {total_sent} invoices in {batches_sent} email(s)."
    if errors:
        summary += f" Errors: {'; '.join(errors)}"
    return {"status": "success" if total_sent > 0 else "error", "message": summary}
@tool(
    name="bulk_send_reminders",
    description="Sends payment reminders to clients with OVERDUE invoices.",
    parameters={
        "type": "object",
        "properties": {
            "client_name": {"type": "string", "description": "Optional. Only send reminders for this client."}
        }
    },
    requires_confirmation=True
)
def bulk_send_reminders(user, args):
    from invoices.services.email_service import send_reminder_email
    qs = Invoice.objects.filter(user=user, status='OVERDUE')
    if args.get('client_name'):
        qs = qs.filter(client_name__icontains=args['client_name'])
    invoices = list(qs)
    if not invoices:
        return {"error": "No overdue invoices found to remind."}
    sent_count = 0
    errors = 0
    for inv in invoices:
        if send_reminder_email(inv, 'REMINDER_AFTER_DUE'):
            sent_count += 1
        else:
            errors += 1
    summary = f"Sent {sent_count} reminders."
    if errors > 0:
        summary += f" {errors} failed (check if clients have emails)."
    return {"status": "success" if sent_count > 0 else "error", "message": summary}
@tool(
    name="bulk_record_payments",
    description="Mark multiple invoices as PAID. Only supports online payment methods (UPI, NEFT, RAZORPAY).",
    parameters={
        "type": "object",
        "properties": {
            "payment_method": {"type": "string", "description": "Required. Must be one of: UPI, NEFT, RAZORPAY"},
            "client_name": {"type": "string", "description": "Optional. Pay all open invoices for this client."},
            "invoice_numbers": {
                "type": "array", 
                "items": {"type": "string"},
                "description": "Optional. List of specific invoice numbers to pay."
            }
        },
        "required": ["payment_method"]
    },
    requires_confirmation=True
)
def bulk_record_payments(user, args):
    method = args['payment_method'].upper()
    if method not in ['UPI', 'NEFT', 'RAZORPAY']:
        return {"error": f"Invalid payment method '{method}'. Only online methods are supported (UPI, NEFT, RAZORPAY)."}
    qs = Invoice.objects.filter(user=user).exclude(status__in=['PAID', 'CANCELLED', 'DRAFT'])
    if args.get('invoice_numbers'):
        qs = qs.filter(invoice_number__in=args['invoice_numbers'])
    elif args.get('client_name'):
        qs = qs.filter(client_name__icontains=args['client_name'])
    else:
        return {"error": "Must provide either client_name or invoice_numbers."}
    invoices = list(qs)
    if not invoices:
        return {"error": "No open invoices found matching criteria."}
    paid_count = 0
    total_paid = Decimal('0.00')
    for inv in invoices:
        remaining = inv.total_amount - sum(p.amount for p in inv.payments.all())
        if remaining > 0:
            Payment.objects.create(invoice=inv, amount=remaining, payment_method=method)
            inv.status = 'PAID'
            inv.save(update_fields=['status'])
            paid_count += 1
            total_paid += remaining
    return {"status": "success", "message": f"Successfully marked {paid_count} invoices as PAID via {method}. Total collected: ₹{total_paid}"}
@tool(
    name="bulk_generate_pdfs",
    description="Generate PDFs for a batch of invoices (does not send emails).",
    parameters={
        "type": "object",
        "properties": {
            "month": {"type": "integer", "description": "Optional. Filter by issue month (1-12)."},
            "year": {"type": "integer", "description": "Optional. Filter by issue year."},
            "client_name": {"type": "string", "description": "Optional. Filter by client."}
        }
    }
)
def bulk_generate_pdfs(user, args):
    from invoices.services.pdf_service import generate_invoice_pdf
    qs = Invoice.objects.filter(user=user)
    if args.get('month'):
        qs = qs.filter(issue_date__month=args['month'])
    if args.get('year'):
        qs = qs.filter(issue_date__year=args['year'])
    if args.get('client_name'):
        qs = qs.filter(client_name__icontains=args['client_name'])
    invoices = list(qs)
    if not invoices:
        return {"error": "No invoices found matching criteria."}
    success_count = 0
    for inv in invoices:
        try:
            generate_invoice_pdf(inv)
            success_count += 1
        except:
            pass
    return {"status": "success", "message": f"Successfully generated {success_count}/{len(invoices)} PDFs. You can download them from the dashboard."}
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