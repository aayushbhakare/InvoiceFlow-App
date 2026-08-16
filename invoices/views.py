from rest_framework import viewsets, permissions, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework import status as http_status
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.models import User
from .models import Invoice, LineItem, Services, Profile, Client, NotificationLog, Payment, RecurringInvoice
from .serializers import (
    InvoiceSerializer, LineItemSerializer, ServicesSerializer,
    ProfileSerializer, RegisterSerializer, ClientSerializer,
    NotificationLogSerializer,PaymentSerializer, RecurringInvoiceSerializer,
)
import json
import hmac
import hashlib
import razorpay
from .ai_agent import process_chat_message
from rest_framework import status
from django.conf import settings
import datetime
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
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status in ['PAID', 'CANCELLED']:
            return Response(
                {'error': f'Cannot send a {invoice.status.lower()} invoice.'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        if not invoice.client or not invoice.client.email:
            return Response(
                {'error': 'Client does not have an email address.'},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        from invoices.services.email_service import send_invoice_email, send_reminder_email
        from invoices.services.whatsapp_service import send_whatsapp_reminder
        if invoice.status == 'DRAFT':
            success_email = send_invoice_email(invoice)
            success_wa = send_whatsapp_reminder(invoice, 'INVOICE_SENT')
            if success_email or success_wa:
                invoice.status = 'SENT'
                invoice.save(update_fields=['status'])
                msg = 'Invoice sent successfully via email'
                if success_wa: msg += ' and WhatsApp'
                return Response({'message': msg})
        else:
            success_email = send_invoice_email(invoice)
            success_wa = send_whatsapp_reminder(invoice, 'REMINDER_AFTER_DUE' if invoice.status == 'OVERDUE' else 'REMINDER_BEFORE_DUE')
            if success_email or success_wa:
                msg = 'Invoice resent successfully via email'
                if success_wa: msg += ' and WhatsApp'
                return Response({'message': msg})
        return Response(
            {'error': 'Failed to send email. Check notification logs for details.'},
            status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        invoice = self.get_object()
        logs = NotificationLog.objects.filter(invoice=invoice)
        serializer = NotificationLogSerializer(logs, many=True)
        return Response(serializer.data)
    @action(detail=True, methods=['get', 'post'])
    def payments(self, request, pk=None):
        invoice = self.get_object()
        if request.method == 'GET':
            payments = invoice.payments.all()
            serializer = PaymentSerializer(payments, many=True)
            return Response(serializer.data)
        else:
            data = request.data.copy()
            data['invoice'] = invoice.id
            serializer = PaymentSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=http_status.HTTP_201_CREATED)
class LineItemViewSet(viewsets.ModelViewSet):
    queryset = LineItem.objects.all()
    serializer_class = LineItemSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return LineItem.objects.filter(invoice__user=self.request.user)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    from invoices.services.pdf_service import generate_invoice_pdf
    pdf_file = generate_invoice_pdf(invoice)
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
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
class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        password = request.data.get('password')
        if not password:
            return Response({"error": "Password is required to delete account."}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if not user.check_password(password):
            return Response({"error": "Incorrect password."}, status=status.HTTP_403_FORBIDDEN)
        Invoice.objects.filter(user=user).delete()
        user.delete()
        return Response({"success": "Account deleted successfully."}, status=status.HTTP_200_OK)
def landing_page(request):
    return render(request, 'index.html')
class RecurringInvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = RecurringInvoiceSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return RecurringInvoice.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_razorpay_order(request, payment_token):
    invoice = get_object_or_404(Invoice, payment_token=payment_token)
    profile = getattr(invoice.user, 'profile', None)
    razorpay_secret = profile.get_razorpay_key_secret() if profile else None
    if not profile or not profile.razorpay_key_id or not razorpay_secret:
        return Response(
            {'error': 'Razorpay keys not configured. Please update your profile.'},
            status=http_status.HTTP_400_BAD_REQUEST
        )
    if invoice.status == 'PAID':
        return Response({'error': 'Invoice is already paid.'}, status=http_status.HTTP_400_BAD_REQUEST)
    client = razorpay.Client(auth=(profile.razorpay_key_id, razorpay_secret))
    amount_in_paise = int(float(invoice.total_amount) * 100)
    order_data = {
        'amount': amount_in_paise,
        'currency': 'INR',
        'receipt': invoice.invoice_number,
        'notes': {
            'invoice_id': str(invoice.id),
            'client_name': invoice.client_name,
        }
    }
    try:
        order = client.order.create(data=order_data)
        return Response({
            'order_id': order['id'],
            'amount': amount_in_paise,
            'currency': 'INR',
            'razorpay_key_id': profile.razorpay_key_id,
            'invoice_number': invoice.invoice_number,
            'client_name': invoice.client_name,
            'client_email': invoice.client.email if invoice.client else '',
        })
    except Exception as e:
        return Response({'error': str(e)}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_razorpay_payment(request, payment_token):
    invoice = get_object_or_404(Invoice, payment_token=payment_token)
    profile = getattr(invoice.user, 'profile', None)
    razorpay_secret = profile.get_razorpay_key_secret() if profile else None
    if not profile or not razorpay_secret:
        return Response({'error': 'Razorpay not configured.'}, status=http_status.HTTP_400_BAD_REQUEST)
    razorpay_order_id = request.data.get('razorpay_order_id')
    razorpay_payment_id = request.data.get('razorpay_payment_id')
    razorpay_signature = request.data.get('razorpay_signature')
    message = f"{razorpay_order_id}|{razorpay_payment_id}"
    expected_signature = hmac.new(
        razorpay_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, razorpay_signature or ''):
        return Response({'error': 'Payment verification failed.'}, status=http_status.HTTP_400_BAD_REQUEST)
    payment = Payment.objects.create(
        invoice=invoice,
        amount=invoice.total_amount,
        payment_method='RAZORPAY',
        payment_date=datetime.date.today(),
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
    )
    invoice.status = 'PAID'
    invoice.save(update_fields=['status'])
    NotificationLog.objects.create(
        invoice=invoice,
        event_type='PAYMENT_RECEIVED',
        delivery_status='SUCCESS',
        metadata={
            'payment_id': razorpay_payment_id,
            'amount': str(invoice.total_amount),
            'method': 'RAZORPAY',
        }
    )
    return Response({'message': 'Payment verified and recorded successfully!'})


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    payload = request.body
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', None)
    if not webhook_secret:
        return Response({'error': 'Webhook secret not configured'}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)
    received_signature = request.headers.get('X-Razorpay-Signature', '')
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, received_signature):
        return Response({'error': 'Invalid signature'}, status=http_status.HTTP_400_BAD_REQUEST)
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return Response({'error': 'Invalid JSON'}, status=http_status.HTTP_400_BAD_REQUEST)
    if event.get('event') == 'payment.captured':
        payment_entity = event['payload']['payment']['entity']
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        amount = payment_entity.get('amount', 0) / 100  
        receipt = payment_entity.get('notes', {}).get('invoice_id')
        if receipt:
            try:
                invoice = Invoice.objects.get(id=int(receipt))
                if invoice.status == 'PAID':
                    return Response({'status': 'already_paid'})
                Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    payment_method='RAZORPAY',
                    razorpay_order_id=order_id,
                    razorpay_payment_id=payment_id,
                )
                invoice.status = 'PAID'
                invoice.save(update_fields=['status'])
                NotificationLog.objects.create(
                    invoice=invoice,
                    event_type='PAYMENT_RECEIVED',
                    delivery_status='SUCCESS',
                    metadata={'payment_id': payment_id, 'amount': str(amount), 'source': 'webhook'}
                )
            except Invoice.DoesNotExist:
                pass
    return Response({'status': 'ok'})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_chat_endpoint(request):
    user_message = request.data.get('message', '')
    pending_action_id = request.data.get('pending_action_id')
    try:
        result = process_chat_message(request.user, user_message, pending_action_id)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
    except Exception as e:
        import logging
        logging.getLogger('invoices').error(f"AI Chat Error for user {request.user.id}: {e}", exc_info=True)

        return Response({"error": "Something went wrong. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)