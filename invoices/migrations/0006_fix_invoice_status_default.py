from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0005_lineitem_service_name_alter_lineitem_services'),
    ]
    operations = [
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('SENT', 'Sent'), ('PAID', 'Paid'), ('OVERDUE', 'Overdue'), ('CANCELLED', 'Cancelled')], default='DRAFT', max_length=20),
        ),
    ]