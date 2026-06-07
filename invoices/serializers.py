from rest_framework import serializers
from decimal import Decimal
from .models import Client, Invoice, LineItem, Services, Profile
import re
from django.contrib.auth.models import User
import requests
import datetime

class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = ['id', 'name', 'description', 'rate']
        read_only_fields = ['id']

class LineItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    service_name = serializers.CharField(source='services.name', read_only=True)
    service_rate = serializers.DecimalField(source='services.rate', read_only=True, max_digits=10, decimal_places=2)

    line_total = serializers.SerializerMethodField()
    class Meta:
        model = LineItem
        fields = ['id', 'invoice', 'services','service_name', 'service_rate','line_total', 'total_hours']
        read_only_fields = ['invoice']
    def get_line_total(self, obj):
        if obj.services and obj.total_hours:
            return round(obj.total_hours * obj.services.rate, 2)
        return 0.00

class InvoiceSerializer(serializers.ModelSerializer):
    items = LineItemSerializer(many=True, source='items')

    subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    taxable_amount = serializers.SerializerMethodField()
    cgst = serializers.SerializerMethodField()
    sgst = serializers.SerializerMethodField()
    igst = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'client_name', 'issue_date', 'due_date', 
            'status', 'discount_percentage', 'items', 
            'subtotal', 'discount_amount', 'total_amount', 'cgst', 'sgst',
            'igst' , 'taxable_amount',
            'client_address', 'client_state', 'tax_rate',
            'bank_details', 'notes'
            ]

    def get_subtotal(self, obj):
        total = 0

        for item in obj.items.all():
            if item.services:
                total += (item.total_hours * item.services.rate)
            else:
                total += 0 
                
        return round(total, 2)

    def get_discount_amount(self, obj):
        subtotal = self.get_subtotal(obj)
        discount = (subtotal * obj.discount_percentage) / Decimal('100.00')
        return round(discount, 2)

    def get_taxable_amount(self, obj):
        subtotal = self.get_subtotal(obj)
        discount = self.get_discount_amount(obj)
        taxable_amount = subtotal - discount
        return float(taxable_amount)

    def get_cgst(self, obj):
        if obj.client_state and obj.client_state.strip().lower() == 'maharashtra':
            taxable = self.get_taxable_amount(obj)
            return round(taxable * (float(obj.tax_rate) / 200), 2)
        return 0.00 
    
    def get_sgst(self, obj):
        if obj.client_state and obj.client_state.strip().lower() == 'maharashtra':
            taxable = self.get_taxable_amount(obj)
            return round(taxable * (float(obj.tax_rate) / 200), 2)
        return 0.00
    
    def get_igst(self, obj):
        if obj.client_state and obj.client_state.strip().lower()!='maharashtra':
            taxable = self.get_taxable_amount(obj)
            return round(taxable * (float(obj.tax_rate) / 100), 2)
        return 0.00

    def get_total_amount(self, obj):
        taxable = self.get_taxable_amount(obj)
        total_tax = self.get_cgst(obj) + self.get_sgst(obj) + self.get_igst(obj)
        return round(taxable + total_tax, 2)

    def create(self, validated_data):
        items_data = validated_data.pop('lineitem_set', [])
        
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            profile = getattr(user, 'profile', None) 
            
            # --- 1. Apply Profile Defaults ---
            if profile:
                if not validated_data.get('bank_details'):
                    validated_data['bank_details'] = getattr(profile, 'default_bank_details', '')
                    
                if not validated_data.get('notes'):
                    validated_data['notes'] = getattr(profile, 'default_notes', '')

            # --- 2. Auto-Generate Invoice Number ---
            current_year = datetime.datetime.now().year
            invoice_count = Invoice.objects.filter(user=user, issue_date__year=current_year).count() + 1
            validated_data['invoice_number'] = f"INV-{current_year}-{invoice_count:04d}"

        # --- 3. Save to Database ---
        if user:
            invoice = Invoice.objects.create(user=user, **validated_data)
        else:
            raise Exception("Cannot create invoice without an authenticated user.")
        
        for item_data in items_data:
            LineItem.objects.create(invoice=invoice, **item_data)
            
        return invoice
    
    def validate(self, attrs):
        if self.instance:
            if self.instance.status == 'PAID':
                raise serializers.ValidationError(
                    {"status": "This invoice is marked as PAID. It is locked and cannot be modified."}
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
                    for attr, value in item.items():
                        setattr(line_item, attr, value)
                    line_item.save()
                    incoming_ids.append(item_id)
                else:
                    item.pop('id', None)
                    LineItem.objects.create(invoice=instance, **item)
            for existing_id, existing_items in existing_items.items():
                if existing_id not in incoming_ids:
                    existing_items.delete()

        return instance
    
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'contact_person', 'email', 'phone', 
            'state', 'address', 'pincode', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
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
    class Meta:
        model = Profile
        fields = ['display_name', 'phone_number', 'upi_id', 'account_number', 'ifsc_code', 'gstin']

    def validate_ifsc_code(self, value):
        value = value.upper()
        if len(value) != 11 or not value.isalnum():
            raise serializers.ValidationError("Invalid IFSC code format.")
        return value

    def create(self, validated_data):
        return self._save_profile(super().create, validated_data)

    def update(self, instance, validated_data):
        return self._save_profile(super().update, validated_data, instance)

    def _save_profile(self, save_method, validated_data, instance=None):
        ifsc = validated_data.get('ifsc_code')
        if ifsc:
            try:
                response = requests.get(f"https://ifsc.razorpay.com/{ifsc}", timeout=5)
                if response.status_code == 200:
                    bank_data = response.json()
                    validated_data['bank_name'] = bank_data.get('BANK')
            except requests.RequestException:
                validated_data['bank_name'] = "Unknown Bank"

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


    
    


