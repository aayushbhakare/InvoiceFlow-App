import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from invoices.models import NotificationLog
from invoices.services.pdf_service import generate_invoice_pdf

logger = logging.getLogger(__name__)


def send_invoice_email(invoice):
    
    client = invoice.client
    if not client or not client.email:
        NotificationLog.objects.create(
            invoice=invoice,
            event_type='INVOICE_SENT',
            delivery_status='FAILED',
            error_message='Client has no email address.',
        )
        return False

    user = invoice.user
    profile = getattr(user, 'profile', None)
    sender_name = getattr(profile, 'display_name', '') or user.email
    from_email = f"{sender_name} via InvoiceFlow <{settings.DEFAULT_FROM_EMAIL}>"

    
    context = {
        'sender_name': sender_name,
        'client_name': client.contact_person or client.name,
        'invoice_number': invoice.invoice_number,
        'issue_date': invoice.issue_date,
        'due_date': invoice.due_date,
        'total_amount': invoice.total_amount,
        'invoice_id': invoice.id,
    }
    html_body = render_to_string('invoices/emails/invoice_sent.html', context)

    
    try:
        pdf_bytes = generate_invoice_pdf(invoice)
    except Exception as e:
        logger.error(f"PDF generation failed for invoice {invoice.invoice_number}: {e}")
        NotificationLog.objects.create(
            invoice=invoice,
            event_type='INVOICE_SENT',
            delivery_status='FAILED',
            recipient_email=client.email,
            error_message=f'PDF generation failed: {str(e)}',
        )
        return False

    
    try:
        email = EmailMessage(
            subject=f"Invoice #{invoice.invoice_number} from {sender_name}",
            body=html_body,
            from_email=from_email,
            to=[client.email],
            reply_to=[user.email],
        )
        email.content_subtype = 'html'
        email.attach(
            f"invoice_{invoice.invoice_number}.pdf",
            pdf_bytes,
            'application/pdf'
        )
        email.send(fail_silently=False)

       
        NotificationLog.objects.create(
            invoice=invoice,
            event_type='INVOICE_SENT',
            delivery_status='SUCCESS',
            recipient_email=client.email,
        )
        return True

    except Exception as e:
        logger.error(f"Email sending failed for invoice {invoice.invoice_number}: {e}")
        NotificationLog.objects.create(
            invoice=invoice,
            event_type='INVOICE_SENT',
            delivery_status='FAILED',
            recipient_email=client.email,
            error_message=str(e),
        )
        return False


def send_reminder_email(invoice, reminder_type, metadata=None):
    client = invoice.client
    if not client or not client.email:
        NotificationLog.objects.create(
            invoice=invoice,
            event_type=reminder_type,
            delivery_status='FAILED',
            error_message='Client has no email address.',
            metadata=metadata,
        )
        return False

    user = invoice.user
    profile = getattr(user, 'profile', None)
    sender_name = getattr(profile, 'display_name', '') or user.email
    from_email = f"{sender_name} via InvoiceFlow <{settings.DEFAULT_FROM_EMAIL}>"

    is_overdue = reminder_type == 'REMINDER_AFTER_DUE'

    context = {
        'sender_name': sender_name,
        'client_name': client.contact_person or client.name,
        'invoice_number': invoice.invoice_number,
        'due_date': invoice.due_date,
        'total_amount': invoice.total_amount,
        'is_overdue': is_overdue,
        'invoice_id': invoice.id,
    }
    html_body = render_to_string('invoices/emails/reminder.html', context)

    try:
        pdf_bytes = generate_invoice_pdf(invoice)
    except Exception as e:
        logger.error(f"PDF generation failed for reminder {invoice.invoice_number}: {e}")
        NotificationLog.objects.create(
            invoice=invoice,
            event_type=reminder_type,
            delivery_status='FAILED',
            recipient_email=client.email,
            error_message=f'PDF generation failed: {str(e)}',
            metadata=metadata,
        )
        return False

    try:
        subject_prefix = "Overdue: " if is_overdue else ""
        email = EmailMessage(
            subject=f"{subject_prefix}Payment Reminder — Invoice #{invoice.invoice_number}",
            body=html_body,
            from_email=from_email,
            to=[client.email],
            reply_to=[user.email],
        )
        email.content_subtype = 'html'
        email.attach(
            f"invoice_{invoice.invoice_number}.pdf",
            pdf_bytes,
            'application/pdf'
        )
        email.send(fail_silently=False)

        NotificationLog.objects.create(
            invoice=invoice,
            event_type=reminder_type,
            delivery_status='SUCCESS',
            recipient_email=client.email,
            metadata=metadata,
        )
        return True

    except Exception as e:
        logger.error(f"Reminder email failed for invoice {invoice.invoice_number}: {e}")
        NotificationLog.objects.create(
            invoice=invoice,
            event_type=reminder_type,
            delivery_status='FAILED',
            recipient_email=client.email,
            error_message=str(e),
            metadata=metadata,
        )
        return False