from rest_framework import serializers
from decimal import Decimal
from .models import Invoice, LineItem, Services, Profile
import re
from django.contrib.auth.models import User

class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = ['id', 'name', 'rate']

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
    items = LineItemSerializer(many=True)

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
        request = self.context.get('request')
        
        if request and hasattr(request, 'user'):
            profile = getattr(request.user, 'company_profile', None)
            
            if profile:
                validated_data['bank_details'] = profile.default_bank_details
                validated_data['notes'] = profile.default_notes

        return super().create(validated_data)
    
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
        fields = [
            'id', 'name', 'display_name', 'entity_type', 
            'phone_number', 'bank_name', 'account_number', 
            'ifsc_code', 'upi_id', 'company_name', 'gstin'
        ]
        read_only_fields = ['id']

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only numbers.")
        phone_regex = "^[6-9]{1}[0-9]{9}$"
        if len(value) != 10 or not re.match(phone_regex, value):
            raise serializers.ValidationError("Phone number must be exactly 10 digits and start with 6, 7, 8, or 9.")
        return value

    def validate_ifsc_code(self, value):

        value = value.upper() 
        ifsc_regex = "^[A-Z]{4}0[A-Z0-9]{6}$"
        if not re.match(ifsc_regex, value):
            raise serializers.ValidationError("Invalid IFSC Code format. Example: SBIN0123456")
        return value

   
    def validate_gstin(self, value):
        if value: 
            value = value.upper()
            if len(value) != 15 or not value.isalnum():
                raise serializers.ValidationError("GSTIN must be exactly 15 alphanumeric characters.")
        return value
    
    


