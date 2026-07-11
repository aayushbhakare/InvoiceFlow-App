from django.db import migrations, models
import uuid
def gen_uuid(apps, schema_editor):
    Invoice = apps.get_model('invoices', 'Invoice')
    for row in Invoice.objects.all():
        row.payment_token = uuid.uuid4()
        row.save(update_fields=['payment_token'])
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0014_alter_profile_razorpay_key_secret'),
    ]
    operations = [
        migrations.AddField(
            model_name='invoice',
            name='payment_token',
            field=models.UUIDField(default=uuid.uuid4, null=True),
        ),
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='invoice',
            name='payment_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]