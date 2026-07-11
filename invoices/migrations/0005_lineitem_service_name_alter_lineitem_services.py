import django.db.models.deletion
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0004_lineitem_rate'),
    ]
    operations = [
        migrations.AddField(
            model_name='lineitem',
            name='service_name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='lineitem',
            name='services',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='invoices.services'),
        ),
    ]