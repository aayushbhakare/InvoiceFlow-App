from rest_framework import serializers
from decimal import Decimal
from .models import Client, Invoice, LineItem, Services, Profile, NotificationLog, Payment, RecurringInvoice
import re
from django.contrib.auth.models import User
import requests
import datetime

def normalize_phone_number(value):
    if not value:
        return value
    cleaned = re.sub(r'[^\d+]', '', value)
    if len(cleaned) == 10 and cleaned.isdigit():
        return f"+91{cleaned}"
    if cleaned.startswith('+') and 11 <= len(cleaned) <= 16:
        return cleaned
    if len(cleaned) == 12 and cleaned.startswith('91'):
        return f"+{cleaned}"
    raise serializers.ValidationError("Invalid phone number format. Enter a 10-digit number or use + country code.")

class ServicesSerializer(serializers.ModelSerializer):
    rate = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    
    class Meta:
        model = Services
        fields = ['id', 'name', 'description', 'rate']
        read_only_fields = ['id']

class LineItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    service_name = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    service_rate = serializers.DecimalField(source='rate', required=False, allow_null=True, max_digits=10, decimal_places=2)
    line_total = serializers.SerializerMethodField()
    
    class Meta:
        model = LineItem
        fields = ['id', 'invoice', 'services','service_name', 'service_rate','line_total', 'total_hours']
        read_only_fields = ['invoice']
    
    def get_line_total(self, obj):
        if obj.rate and obj.total_hours:
            return round(obj.total_hours * obj.rate, 2)
        return 0.00

class InvoiceSerializer(serializers.ModelSerializer):
    items = LineItemSerializer(many=True)
    subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    taxable_amount = serializers.SerializerMethodField()
    cgst = serializers.SerializerMethodField()
    sgst = serializers.SerializerMethodField()
    igst = serializers.SerializerMethodField()
    amount_paid = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'client_name', 'issue_date', 'due_date', 
            'status', 'discount_percentage', 'items', 
            'subtotal', 'discount_amount', 'total_amount', 'cgst', 'sgst',
            'igst' , 'taxable_amount',
            'client_address', 'client_state', 'tax_rate',
            'bank_details', 'notes', 'client', 'amount_paid', 'balance_due'
            ]
        read_only_fields = ['invoice_number']
    
    def get_subtotal(self, obj):
        if not hasattr(obj, '_cached_subtotal'):
            total = 0
            for item in obj.items.all():
                if item.rate and item.total_hours:
                    total += (item.total_hours * item.rate)
            obj._cached_subtotal = round(total, 2)
        return obj._cached_subtotal
    
    def get_discount_amount(self, obj):
        subtotal = self.get_subtotal(obj)
        discount = (subtotal * obj.discount_percentage) / Decimal('100.00')
        return round(discount, 2)
    
    def get_taxable_amount(self, obj):
        subtotal = self.get_subtotal(obj)
        discount = self.get_discount_amount(obj)
        return float(subtotal - discount)
    
    def _get_seller_state(self, obj):
        try:
            return obj.user.profile.state.strip().lower() if obj.user.profile.state else 'maharashtra'
        except:
            return 'maharashtra'
    
    def get_cgst(self, obj):
        if obj.client_state and obj.client_state.strip().lower() == self._get_seller_state(obj):
            taxable = self.get_taxable_amount(obj)
            return round(taxable * (float(obj.tax_rate) / 200), 2)
        return 0.00 
    
    def get_sgst(self, obj):
        if obj.client_state and obj.client_state.strip().lower() == self._get_seller_state(obj):
            taxable = self.get_taxable_amount(obj)
            return round(taxable * (float(obj.tax_rate) / 200), 2)
        return 0.00
    
    def get_igst(self, obj):
        if not obj.client_state or obj.client_state.strip().lower() != self._get_seller_state(obj):
            taxable = self.get_taxable_amount(obj)
            return round(taxable * (float(obj.tax_rate) / 100), 2)
        return 0.00
    
    def get_amount_paid(self, obj):
        return float(sum(p.amount for p in obj.payments.all()))
    
    def get_balance_due(self, obj):
        total = self.get_total_amount(obj)
        paid = self.get_amount_paid(obj)
        return round(total - paid, 2)
    
    def get_total_amount(self, obj):
        taxable = self.get_taxable_amount(obj)
        total_tax = self.get_cgst(obj) + self.get_sgst(obj) + self.get_igst(obj)
        return round(taxable + total_tax, 2)
    
    def get_total_amount_from_items(self, items_data, validated_data):
        from decimal import Decimal
        subtotal = Decimal('0')
        for item in items_data:
            service = item.get('services')
            hours = item.get('total_hours', 0)
            if service and hasattr(service, 'rate'):
                subtotal += Decimal(str(hours)) * service.rate
        discount = (subtotal * validated_data.get('discount_percentage', Decimal('0'))) / Decimal('100')
        taxable = subtotal - discount
        tax_rate = validated_data.get('tax_rate', Decimal('0'))
        tax = taxable * (tax_rate / Decimal('100'))
        return round(taxable + tax, 2)
    
    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        if not user:
            raise serializers.ValidationError("Cannot create invoice without an authenticated user.")
        profile = getattr(user, 'profile', None)
        if profile:
            if not validated_data.get('bank_details'):
                validated_data['bank_details'] = getattr(profile, 'default_bank_details', '')
            if not validated_data.get('notes'):
                validated_data['notes'] = getattr(profile, 'default_notes', '')
        validated_data['total_amount'] = self.get_total_amount_from_items(items_data, validated_data)
        invoice = Invoice.objects.create(user=user, **validated_data)
        for item_data in items_data:
            service = item_data.get('services')
            if service is not None:
                item_data['rate'] = service.rate
                item_data['service_name'] = service.name   
            LineItem.objects.create(invoice=invoice, **item_data)
        return invoice
    
    def validate(self, attrs):
        if self.instance:
            if self.instance.status == 'PAID':
                raise serializers.ValidationError(
                    {"status": "This invoice is marked as PAID. It is locked and cannot be modified."}
                )  
        client_name = attrs.get('client_name')
        if not client_name and self.instance:
            client_name = self.instance.client_name
        if client_name and Client.objects.filter(name=client_name, is_active=False).exists():
            raise serializers.ValidationError(
                {"client_name": "Cannot create or modify an invoice for an inactive client."}
            )
        return attrs
    
    def update(self, instance, validated_data):
        item_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if item_data is not None:
            existing_items = {}
            all_items = instance.items.all()
            for item in all_items:
                existing_items[item.id] = item
            incoming_ids = []
            for item in item_data:
                item_id = item.get('id', None)
                if item_id and item_id in existing_items:
                    line_item = existing_items[item_id]
                    new_service = item.get('services', line_item.services)
                    if new_service and new_service != line_item.services:
                        item['rate'] = new_service.rate
                        item['service_name'] = new_service.name
                    for attr, value in item.items():
                        setattr(line_item, attr, value)
                    line_item.save()
                    incoming_ids.append(item_id)
                else:
                    item.pop('id', None)
                    service = item.get('services')
                    if service is not None:
                        item['rate'] = service.rate
                        item['service_name'] = service.name
                    LineItem.objects.create(invoice=instance, **item)
            for existing_id, existing_item in existing_items.items():
                if existing_id not in incoming_ids:
                    existing_item.delete()
        return instance

class ClientSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()
    total_billed = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone', 'status', 'city',
            'state', 'address', 'pincode', 'is_active', 'created_at', 'invoice_count', 'total_billed'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_status(self, obj):
        return 'active' if obj.is_active else 'inactive'
    
    def get_invoice_count(self, obj):
        return obj.invoices.count()
    
    def get_total_billed(self, obj):
        from decimal import Decimal
        return float(sum(
            inv.total_amount or Decimal('0')
            for inv in obj.invoices.all()
    ))
    
    def validate_phone(self, value):
        return normalize_phone_number(value)

class RegisterSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ('email', 'password') 
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8},
            'email': {'required': True}
        }
    
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'], 
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class ProfileSerializer(serializers.ModelSerializer):
    is_complete = serializers.SerializerMethodField()
    has_razorpay_secret = serializers.SerializerMethodField()
    has_swiftpay_secret = serializers.SerializerMethodField()
    email=serializers.ReadOnlyField(source='user.email')
    
    class Meta:
        model = Profile
        fields = ['display_name', 'phone_number', 'upi_id', 'account_number', 'email', 'ifsc_code', 'gstin', 'is_complete',
          'street_address', 'city', 'state', 'pincode', 'razorpay_key_id', 'razorpay_key_secret', 'has_razorpay_secret',
          'swiftpay_key_id', 'swiftpay_key_secret', 'has_swiftpay_secret', 'preferred_gateway']
        extra_kwargs = {
            'razorpay_key_secret': {'write_only': True},
            'swiftpay_key_secret': {'write_only': True},
        }
    
    def get_is_complete(self, obj):
        required_fields = [obj.bank_name, obj.account_number, obj.ifsc_code]
        return all(field for field in required_fields)
    
    def get_has_razorpay_secret(self, obj):
        return bool(obj.razorpay_key_secret)
        
    def get_has_swiftpay_secret(self, obj):
        return bool(obj.swiftpay_key_secret)
    
    def validate_ifsc_code(self, value):
        value = value.upper()
        if len(value) != 11 or not value.isalnum():
            raise serializers.ValidationError("Invalid IFSC code format.")
        return value
    
    def validate_phone_number(self, value):
        return normalize_phone_number(value)
    
    def create(self, validated_data):
        return self._save_profile(super().create, validated_data)
    
    def update(self, instance, validated_data):
        return self._save_profile(super().update, validated_data, instance)
    
    def _save_profile(self, save_method, validated_data, instance=None):
        ifsc = validated_data.get('ifsc_code')
        if ifsc and not validated_data.get('bank_name'):
            try:
                response = requests.get(f"https://ifsc.razorpay.com/{ifsc}", timeout=2)
                if response.status_code == 200:
                    validated_data['bank_name'] = response.json().get('BANK', '')
            except requests.RequestException:
                pass  
        self._assign_entity_type(validated_data)
        if instance:
            return save_method(instance, validated_data)
        return save_method(validated_data)
    
    def _assign_entity_type(self, validated_data):
        gstin = validated_data.get('gstin')
        if not gstin:
            validated_data['entity_type'] = 'Individual'
            return
        gstin = gstin.upper()
        if len(gstin) >= 6:
            entity_char = gstin[5] 
            if entity_char == 'P':
                validated_data['entity_type'] = 'Individual/Proprietor'
            elif entity_char == 'C':
                validated_data['entity_type'] = 'Company'
            elif entity_char == 'F':
                validated_data['entity_type'] = 'Partnership Firm'
            elif entity_char == 'H':
                validated_data['entity_type'] = 'HUF'
            elif entity_char == 'T':
                validated_data['entity_type'] = 'Trust'
            else:
                validated_data['entity_type'] = 'Other'
        else:
            validated_data['entity_type'] = 'Individual'

class NotificationLogSerializer(serializers.ModelSerializer):
    event_display = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'event_type', 'event_display', 'timestamp',
            'delivery_status', 'recipient_email', 'error_message', 'metadata',
        ]
        read_only_fields = fields
    
    def get_event_display(self, obj):
        display_map = {
            'INVOICE_SENT': 'Invoice Sent',
            'REMINDER_BEFORE_DUE': 'Reminder Sent (before due date)',
            'REMINDER_ON_DUE': 'Reminder Sent (on due date)',
            'REMINDER_AFTER_DUE': 'Reminder Sent (overdue)',
            'PAYMENT_RECEIVED': 'Payment Received',
            'STATUS_CHANGED': 'Status Changed',
        }
        return display_map.get(obj.event_type, obj.event_type)

class PaymentSerializer(serializers.ModelSerializer):
    payment_method_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = ['id', 'invoice', 'amount', 'payment_date', 'payment_method',
                  'payment_method_display', 'reference_number', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_payment_method_display(self, obj):
        return obj.get_payment_method_display()
    
    def validate(self, attrs):
        invoice = attrs['invoice']
        if invoice.status == 'CANCELLED':
            raise serializers.ValidationError("Cannot record payment for a cancelled invoice.")
        existing_paid = sum(p.amount for p in invoice.payments.all())
        if existing_paid + attrs['amount'] > invoice.total_amount:
            raise serializers.ValidationError(
                f"Payment of ₹{attrs['amount']} exceeds remaining balance of ₹{invoice.total_amount - existing_paid}."
            )
        return attrs
    
    def create(self, validated_data):
        payment = super().create(validated_data)
        invoice = payment.invoice
        total_paid = sum(p.amount for p in invoice.payments.all())
        if total_paid >= invoice.total_amount:
            invoice.status = 'PAID'
            invoice.save(update_fields=['status'])
            NotificationLog.objects.create(
                invoice=invoice,
                event_type='PAYMENT_RECEIVED',
                delivery_status='SUCCESS',
                metadata={'amount': str(payment.amount), 'method': payment.payment_method,
                          'total_paid': str(total_paid)},
            )
        return payment
    
class RecurringInvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.name', read_only=True)
    frequency_display = serializers.SerializerMethodField()
    
    class Meta:
        model = RecurringInvoice
        fields = ['id', 'client', 'client_name', 'frequency', 'frequency_display',
                  'next_issue_date', 'end_date', 'max_occurrences', 
                  'completed_occurrences', 'is_active', 'template_data', 'created_at']
        read_only_fields = ['id', 'created_at', 'completed_occurrences']
    
    def get_frequency_display(self, obj):
        return obj.get_frequency_display()