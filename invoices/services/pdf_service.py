import weasyprint
from django.template.loader import render_to_string
from invoices.models import Invoice, Client
from invoices.serializers import InvoiceSerializer


def generate_invoice_pdf(invoice):
    """
    Generate a PDF for the given invoice.

    Args:
        invoice: Invoice model instance

    Returns:
        bytes: Raw PDF file content
    """
    serializer = InvoiceSerializer(invoice)
    invoice_data = serializer.data

    # Fetch client pincode (not stored on invoice, fetched from Client model)
    try:
        client_obj = Client.objects.get(id=invoice_data['client'])
        invoice_data['client_pincode'] = client_obj.pincode or ''
    except Client.DoesNotExist:
        invoice_data['client_pincode'] = ''

    # Build billed_from from user profile
    user = invoice.user
    profile = getattr(user, 'profile', None)

    bank_parts = []
    if profile:
        if getattr(profile, 'bank_name', None):
            bank_parts.append(f"Bank: {profile.bank_name}")
        if getattr(profile, 'account_number', None):
            bank_parts.append(f"Account No: {profile.account_number}")
        if getattr(profile, 'ifsc_code', None):
            bank_parts.append(f"IFSC: {profile.ifsc_code}")
        if getattr(profile, 'upi_id', None):
            bank_parts.append(f"UPI: {profile.upi_id}")

    context = {
        'invoice': invoice_data,
        'line_items': invoice_data.get('items', []),
        'billed_from': {
            'name': getattr(profile, 'display_name', '') or user.email,
            'gstin': getattr(profile, 'gstin', '') or '',
            'phone': getattr(profile, 'phone_number', '') or '',
            'email': user.email,
        },
        'bank_details': '\n'.join(bank_parts),
    }

    html_string = render_to_string('invoices/invoice.html', context)
    pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()

    return pdf_bytes