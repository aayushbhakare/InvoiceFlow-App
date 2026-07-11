import logging
from django.conf import settings
from twilio.rest import Client
from invoices.models import NotificationLog
logger = logging.getLogger(__name__)
def send_whatsapp_reminder(invoice, event_type):
    if not invoice.client or not invoice.client.phone:
        logger.warning(f"Cannot send WhatsApp reminder for invoice {invoice.invoice_number}: No client phone number.")
        return False
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_WHATSAPP_NUMBER]):
        logger.error("Twilio credentials not fully configured in settings.")
        return False
    try:
        twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        from_number = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
        to_number = invoice.client.phone
        if not to_number.startswith('+'):
            to_number = f"+91{to_number}" 
        to_number = f"whatsapp:{to_number}"
        base_url = getattr(settings, 'PAYMENT_BASE_URL', 'http://127.0.0.1:5500')
        pay_link = f"{base_url}/frontend/pay.html?token={invoice.payment_token}"
        if event_type == 'REMINDER_BEFORE_DUE':
            greeting = f"Friendly reminder: Your invoice {invoice.invoice_number} is due soon on {invoice.due_date}."
        elif event_type == 'REMINDER_ON_DUE':
            greeting = f"This is a reminder that invoice {invoice.invoice_number} is due today."
        elif event_type == 'REMINDER_AFTER_DUE':
            greeting = f"URGENT: Your invoice {invoice.invoice_number} was due on {invoice.due_date} and is now overdue."
        else:
            greeting = f"Update regarding your invoice {invoice.invoice_number}."
        provider_name = "Your Service Provider"
        if hasattr(invoice.user, 'profile') and invoice.user.profile.display_name:
            provider_name = invoice.user.profile.display_name
        message_body = (
            f"Hello {invoice.client.name},\n\n"
            f"{greeting}\n\n"
            f"Amount Due: ₹{invoice.total_amount}\n"
            f"You can pay securely here: {pay_link}\n\n"
            f"Thank you,\n{provider_name}"
        )
        message = twilio_client.messages.create(
            from_=from_number,
            body=message_body,
            to=to_number
        )
        logger.info(f"WhatsApp reminder sent successfully to {invoice.client.phone} (SID: {message.sid})")
        NotificationLog.objects.create(
            invoice=invoice,
            event_type=event_type,
            delivery_status='SUCCESS',
            recipient_email=invoice.client.phone, 
            metadata={'channel': 'whatsapp', 'message_sid': message.sid}
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp reminder for invoice {invoice.invoice_number}: {e}", exc_info=True)
        NotificationLog.objects.create(
            invoice=invoice,
            event_type=event_type,
            delivery_status='FAILED',
            recipient_email=invoice.client.phone,
            error_message=str(e),
            metadata={'channel': 'whatsapp'}
        )
        return False