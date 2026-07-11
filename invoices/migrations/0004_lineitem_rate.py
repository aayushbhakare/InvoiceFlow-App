from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0003_client_city'),
    ]
    operations = [
        migrations.AddField(
            model_name='lineitem',
            name='rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]