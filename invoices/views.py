from urllib3 import request
import weasyprint
from rest_framework import viewsets, permissions
from .models import Invoice, LineItem, Services, Profile, Client
from .serializers import InvoiceSerializer, LineItemSerializer, ServicesSerializer, ProfileSerializer, RegisterSerializer, ClientSerializer
from rest_framework.permissions import IsAuthenticated
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User


class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServicesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Services.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user).order_by('-issue_date')

    # def perform_create(self, validated_data):
    #     invoice = Invoice.objects.create(**validated_data)
    #     return invoice

class LineItemViewSet(viewsets.ModelViewSet):
    queryset = LineItem.objects.all()
    serializer_class = LineItemSerializer

    def get_queryset(self):
        return LineItem.objects.filter(invoice__user=self.request.user)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    serializer = InvoiceSerializer(invoice)
    invoice_data = serializer.data

    # Fetch client pincode (not stored on invoice, fetched from Client model)
    from .models import Client
    try:
        client_obj = Client.objects.get(id=invoice_data['client'])
        invoice_data['client_pincode'] = client_obj.pincode or ''
    except Client.DoesNotExist:
        invoice_data['client_pincode'] = ''

    # Build billed_from from user profile
    profile = getattr(request.user, 'profile', None)
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
            'name': getattr(profile, 'display_name', '') or request.user.email,
            'gstin': getattr(profile, 'gstin', '') or '',
            'phone': getattr(profile, 'phone_number', '') or '',
            'email': request.user.email,
        },
        'bank_details': '\n'.join(bank_parts),
    }

    html_string = render_to_string('invoices/invoice.html', context)
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice_data["invoice_number"]}.pdf"'
    return response

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny] 
    serializer_class = RegisterSerializer

class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Client.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        if 'status' in request.data:
            request.data['is_active'] = request.data['status'] == 'active'
        return super().partial_update(request, *args, **kwargs)

class ProfileManageView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated] 

    def get_object(self):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile

def landing_page(request):
    return render(request, 'landingpage.html')