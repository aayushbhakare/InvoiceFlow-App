

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