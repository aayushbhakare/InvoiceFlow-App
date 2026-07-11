from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0002_profile_city_profile_pincode_profile_state_and_more'),
    ]
    operations = [
        migrations.AddField(
            model_name='client',
            name='city',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]