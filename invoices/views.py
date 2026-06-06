import weasyprint
from rest_framework import viewsets
from .models import Invoice, LineItem, Services
from .serializers import InvoiceSerializer, LineItemSerializer, ServicesSerializer
from rest_framework.permissions import IsAuthenticated
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Invoice
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from .serializers import RegisterSerializer

class ServicesViewSet(viewsets.ModelViewSet):
    queryset = Services.objects.all()
    serializer_class = ServicesSerializer

class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

class LineItemViewSet(viewsets.ModelViewSet):
    queryset = LineItem.objects.all()
    serializer_class = LineItemSerializer

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    serializer = InvoiceSerializer(invoice)
    invoice_data = serializer.data
    context = {
        'invoice': invoice_data,
        'line_items': invoice_data.get('items', [])
    }
    html_string = render_to_string('invoices/invoice.html', context)
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoices_{invoice_data["invoice_number"]}.pdf"'
    return response


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny] 
    serializer_class = RegisterSerializer

