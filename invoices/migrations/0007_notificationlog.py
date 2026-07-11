import django.db.models.deletion
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0006_fix_invoice_status_default'),
    ]
    operations = [
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('INVOICE_SENT', 'Invoice Sent'), ('REMINDER_BEFORE_DUE', 'Reminder Before Due Date'), ('REMINDER_ON_DUE', 'Reminder On Due Date'), ('REMINDER_AFTER_DUE', 'Reminder After Due Date'), ('PAYMENT_RECEIVED', 'Payment Received'), ('STATUS_CHANGED', 'Status Changed')], max_length=30)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('delivery_status', models.CharField(choices=[('PENDING', 'Pending'), ('SUCCESS', 'Success'), ('FAILED', 'Failed')], default='PENDING', max_length=10)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('recipient_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('metadata', models.JSONField(blank=True, null=True)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_logs', to='invoices.invoice')),
            ],
            options={
                'ordering': ['-timestamp'],
                'indexes': [models.Index(fields=['invoice', 'event_type'], name='invoices_no_invoice_894dcc_idx'), models.Index(fields=['invoice', 'timestamp'], name='invoices_no_invoice_581a4e_idx')],
            },
        ),
    ]