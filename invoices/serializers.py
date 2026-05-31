from rest_framework import serializers
from decimal import Decimal
from .models import Invoice, LineItem, Services

class ServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Services
        fields = ['id', 'name', 'rate']

class LineItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    service_name = serializers.CharField(source='services.name', read_only=True)
    service_rate = serializers.DecimalField(source='services.rate', read_only=True, max_digits=10, decimal_places=2)
    class Meta:
        model = LineItem
        fields = ['id', 'invoice', 'services','service_name', 'service_rate', 'total_hours']
        read_only_fields = ['invoice']

class InvoiceSerializer(serializers.ModelSerializer):
    items = LineItemSerializer(many=True)

    subtotal = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'client_name', 'issue_date', 'due_date', 
            'status', 'discount_percentage', 'items', 
            'subtotal', 'discount_amount', 'total_amount']

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

    def get_total_amount(self, obj):
        subtotal = self.get_subtotal(obj)
        discount = self.get_discount_amount(obj)
        total_amount = subtotal - discount
        return round(total_amount, 2) 

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        invoice = Invoice.objects.create(**validated_data)
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
    


