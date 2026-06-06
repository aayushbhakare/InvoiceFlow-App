from django.db import models
from django.contrib.auth.models import User

from django.db import models

class Services(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.name

class Invoice(models.Model):

    status_choices = STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('CANCELLED', 'Cancelled'),
    )

    invoice_number = models.CharField(max_length=25, unique=True)
    client_name = models.CharField(max_length=100)
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=status_choices, default='Draft')
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    client_state = models.CharField(max_length=50, blank=True, null=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    client_address = models.TextField(null=True, blank=True)
    bank_details = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client_name}"


class LineItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    services = models.ForeignKey(Services, on_delete=models.PROTECT, null=True)
    total_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        # 1. Check if the service actually exists on this row
        if self.services:
            return f"LineItem for {self.invoice.invoice_number} - {self.services.name}"
        else:
            return f"LineItem for {self.invoice.invoice_number} - [No Service Attached]"



class Profile(models.Model):
    ENTITY_CHOICES = (
        ('INDIVIDUAL', 'Individual / Freelancer'),
        ('COMPANY', 'Registered Company'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
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

    def __str__(self):
        return f"{self.display_name} ({self.get_entity_type_display()})"