from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0013_payment_razorpay_order_id_and_more'),
    ]
    operations = [
        migrations.AlterField(
            model_name='profile',
            name='razorpay_key_secret',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
    ]