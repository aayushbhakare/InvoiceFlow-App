import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from invoices.models import Invoice, NotificationLog, RecurringInvoice, LineItem, Services
from invoices.services.email_service import send_reminder_email, send_invoice_email
from invoices.services.whatsapp_service import send_whatsapp_reminder
from dateutil.relativedelta import relativedelta
logger = logging.getLogger(__name__)
@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_invoice_email_task(self, invoice_id):
    try:
        invoice = Invoice.objects.get(id=invoice_id)
        success = send_invoice_email(invoice)
        if not success:
            raise Exception(f"Email service returned failure for invoice {invoice_id}")
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found — cannot send email.")
    except Exception as exc:
        logger.error(f"Failed to send email for invoice {invoice_id}: {exc}")
        self.retry(exc=exc)
@shared_task
def scan_upcoming_reminders():
    today = timezone.now().date()
    reminder_schedule = [
        (-3, 'REMINDER_BEFORE_DUE'),
        (0, 'REMINDER_ON_DUE'),
        (3, 'REMINDER_AFTER_DUE'),
        (7, 'REMINDER_AFTER_DUE'),
    ]
    sent_invoices = Invoice.objects.filter(
        status__in=['SENT', 'OVERDUE'],
    ).select_related('client')
    reminders_sent = 0
    for invoice in sent_invoices:
        if not invoice.client or not invoice.client.email:
            continue
        for day_offset, reminder_type in reminder_schedule:
            target_date = invoice.due_date + timedelta(days=day_offset)
            if target_date != today:
                continue
            already_sent = NotificationLog.objects.filter(
                invoice=invoice,
                event_type=reminder_type,
                delivery_status='SUCCESS',
                metadata__day_offset=day_offset,
            ).exists()
            if already_sent:
                logger.info(
                    f"Skipping duplicate reminder for {invoice.invoice_number} "
                    f"(type={reminder_type}, offset={day_offset})"
                )
                continue
            success_email = send_reminder_email(
                invoice,
                reminder_type,
                metadata={'day_offset': day_offset},
            )
            success_wa = send_whatsapp_reminder(
                invoice,
                reminder_type
            )
            if success_email or success_wa:
                reminders_sent += 1
                logger.info(
                    f"Reminder sent for {invoice.invoice_number} "
                    f"(type={reminder_type}, offset={day_offset})"
                )
    logger.info(f"scan_upcoming_reminders complete: {reminders_sent} reminders sent.")
@shared_task
def scan_overdue_invoices():
    today = timezone.now().date()
    overdue_invoices = Invoice.objects.filter(
        status='SENT',
        due_date__lt=today,
    )
    count = 0
    for invoice in overdue_invoices:
        invoice.status = 'OVERDUE'
        invoice.save(update_fields=['status'])
        NotificationLog.objects.create(
            invoice=invoice,
            event_type='STATUS_CHANGED',
            delivery_status='SUCCESS',
            metadata={'from': 'SENT', 'to': 'OVERDUE'},
        )
        count += 1
        logger.info(f"Invoice {invoice.invoice_number} marked as OVERDUE")
    logger.info(f"scan_overdue_invoices complete: {count} invoices marked overdue.")
@shared_task
def generate_recurring_invoices():
    today = timezone.now().date()
    templates = RecurringInvoice.objects.filter(is_active=True, next_issue_date__lte=today)
    count = 0
    for template in templates:
        data = template.template_data
        if template.end_date and today > template.end_date:
            template.is_active = False
            template.save()
            continue
        if template.max_occurrences and template.completed_occurrences >= template.max_occurrences:
            template.is_active = False
            template.save()
            continue
        invoice = Invoice.objects.create(
            user=template.user,
            client=template.client,
            client_name=template.client.name,
            client_state=template.client.state,
            client_address=template.client.address,
            issue_date=today,
            due_date=today + timedelta(days=30),
            discount_percentage=data.get('discount_percentage', 0),
            tax_rate=data.get('tax_rate', 18),
            notes=data.get('notes', ''),
        )
        template.completed_occurrences += 1
        for item in data.get('items', []):
            service = Services.objects.filter(id=item.get('service_id')).first()
            LineItem.objects.create(
                invoice=invoice,
                services=service,
                service_name=item.get('service_name', ''),
                rate=item.get('rate', 0),
                total_hours=item.get('hours', 0),
            )
        from invoices.serializers import InvoiceSerializer
        invoice.refresh_from_db()
        serializer = InvoiceSerializer(invoice)
        invoice.total_amount = serializer.data['total_amount']
        invoice.save(update_fields=['total_amount'])
        if template.frequency == 'WEEKLY':
            template.next_issue_date += timedelta(weeks=1)
        elif template.frequency == 'MONTHLY':
            template.next_issue_date += relativedelta(months=1)
        elif template.frequency == 'QUARTERLY':
            template.next_issue_date += relativedelta(months=3)
        template.save()
        count += 1
        logger.info(f"Recurring invoice created for {template.client.name}: {invoice.invoice_number}")
    logger.info(f"generate_recurring_invoices complete: {count} invoices created.")