from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0008_payment'),
    ]
    operations = [
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(choices=[('UPI', 'UPI'), ('NET_BANKING', 'Net Banking'), ('NEFT', 'NEFT/RTGS/IMPS'), ('RAZORPAY', 'Razorpay')], default='BANK_TRANSFER', max_length=20),
        ),
    ]