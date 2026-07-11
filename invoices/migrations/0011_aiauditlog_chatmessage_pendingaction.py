import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0010_recurringinvoice'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='AIAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conversation_id', models.CharField(blank=True, max_length=64, null=True)),
                ('initiated_by', models.CharField(default='user', max_length=8)),
                ('trigger_event', models.CharField(blank=True, max_length=64, null=True)),
                ('user_prompt', models.TextField(blank=True, null=True)),
                ('tool_name', models.CharField(max_length=64)),
                ('tool_args', models.JSONField()),
                ('required_confirmation', models.BooleanField()),
                ('status', models.CharField(max_length=12)),
                ('result', models.JSONField(blank=True, null=True)),
                ('duration_ms', models.IntegerField(default=0)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('model', 'Model')], max_length=10)),
                ('content', models.TextField(blank=True, null=True)),
                ('tool_calls', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='PendingAction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('conversation_id', models.CharField(blank=True, max_length=64, null=True)),
                ('initiated_by', models.CharField(choices=[('user', 'User'), ('system', 'System')], default='user', max_length=8)),
                ('tool_name', models.CharField(max_length=64)),
                ('tool_args', models.JSONField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('expired', 'Expired')], default='pending', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]