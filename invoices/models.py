from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
import uuid
from datetime import timedelta


class Services(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services', null=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name
    
class Client(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients', null=True)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    city = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class Invoice(models.Model):

    status_choices = STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='invoices', null=True, blank=True)
    invoice_number = models.CharField(max_length=25, unique=True)
    client_name = models.CharField(max_length=100)
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=status_choices, default='DRAFT')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    client_state = models.CharField(max_length=50, blank=True, null=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    client_address = models.TextField(null=True, blank=True)
    bank_details = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client_name}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            now = timezone.now()
            year = now.strftime('%Y')
            month = now.strftime('%m')
            
            prefix = f"INV-{year}-{month}-"
            
            last_invoice = Invoice.objects.filter(
                invoice_number__startswith=prefix
            ).order_by('id').last()
            
            if last_invoice:
                try:
                    last_sequence_str = last_invoice.invoice_number.split('-')[-1]
                    last_sequence = int(last_sequence_str)
                    self.invoice_number = f"{prefix}{last_sequence + 1:04d}"
                except (ValueError, IndexError):
                    self.invoice_number = f"{prefix}0001"
            else:
                self.invoice_number = f"{prefix}0001"
                
        super().save(*args, **kwargs)


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    services = models.ForeignKey(Services, on_delete=models.SET_NULL, null=True)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    service_name = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        name = self.service_name or (self.services.name if self.services else None)
        return f"LineItem for {self.invoice.invoice_number} - {name or '[No Service Attached]'}"



class Profile(models.Model):
    ENTITY_CHOICES = (
        ('INDIVIDUAL', 'Individual / Freelancer'),
        ('COMPANY', 'Registered Company'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', null=True)
    name = models.CharField(max_length=255, default="") 
    display_name = models.CharField(max_length=255, default="") 
    entity_type = models.CharField(max_length=20, choices=ENTITY_CHOICES, default='INDIVIDUAL')
    phone_number = models.CharField(max_length=15, default="") 
    bank_name = models.CharField(max_length=255, default="")
    account_number = models.CharField(max_length=50, default="")
    ifsc_code = models.CharField(max_length=20, default="")
    upi_id = models.CharField(max_length=100, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True) 
    gstin = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    street_address = models.TextField(blank=True, null=True) 
    razorpay_key_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_key_secret = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.display_name} ({self.get_entity_type_display()})"


class NotificationLog(models.Model):
    EVENT_TYPES = (
        ('INVOICE_SENT', 'Invoice Sent'),
        ('REMINDER_BEFORE_DUE', 'Reminder Before Due Date'),
        ('REMINDER_ON_DUE', 'Reminder On Due Date'),
        ('REMINDER_AFTER_DUE', 'Reminder After Due Date'),
        ('PAYMENT_RECEIVED', 'Payment Received'),
        ('STATUS_CHANGED', 'Status Changed'),
    )

    DELIVERY_STATUSES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    )

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='notification_logs')
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=10, choices=DELIVERY_STATUSES, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    recipient_email = models.EmailField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['invoice', 'event_type']),
            models.Index(fields=['invoice', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.invoice.invoice_number} — {self.get_event_type_display()} ({self.delivery_status})"
    
class Payment(models.Model):
    PAYMENT_METHODS = (
    ('UPI', 'UPI'),
    ('NET_BANKING', 'Net Banking'),
    ('NEFT', 'NEFT/RTGS/IMPS'),
    ('RAZORPAY', 'Razorpay'),
   )

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='BANK_TRANSFER')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"Payment of ₹{self.amount} for {self.invoice.invoice_number}"

class RecurringInvoice(models.Model):
    FREQUENCY_CHOICES = (
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_invoices')
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='MONTHLY')
    next_issue_date = models.DateField()           
    end_date = models.DateField(null=True, blank=True)  
    max_occurrences = models.IntegerField(null=True, blank=True)  
    completed_occurrences = models.IntegerField(default=0)        
    is_active = models.BooleanField(default=True)
    template_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Recurring: {self.client.name} ({self.get_frequency_display()})"
    
class ChatMessage(models.Model):
    """Stores AI conversation history. Auto-purged after 16 hours."""
    ROLE_CHOICES = (('user', 'User'), ('model', 'Model'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_history')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(blank=True, null=True)
    tool_calls = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    @classmethod
    def cleanup_old_messages(cls, user):
        cutoff = timezone.now() - timedelta(hours=16)
        cls.objects.filter(user=user, created_at__lt=cutoff).delete()
class PendingAction(models.Model):
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation_id = models.CharField(max_length=64, null=True, blank=True)
    initiated_by = models.CharField(max_length=8, choices=[('user','User'),('system','System')], default='user')
    tool_name = models.CharField(max_length=64)
    tool_args = models.JSONField()
    status = models.CharField(
        max_length=12,
        choices=[('pending','Pending'),('approved','Approved'),
                 ('rejected','Rejected'),('expired','Expired')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

class AIAuditLog(models.Model):
    
    conversation_id = models.CharField(max_length=64, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    initiated_by = models.CharField(max_length=8, default='user')
    trigger_event = models.CharField(max_length=64, null=True, blank=True)
    user_prompt = models.TextField(null=True, blank=True)
    tool_name = models.CharField(max_length=64)
    tool_args = models.JSONField()
    required_confirmation = models.BooleanField()
    status = models.CharField(max_length=12)
    result = models.JSONField(null=True, blank=True)
    duration_ms = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)


    


