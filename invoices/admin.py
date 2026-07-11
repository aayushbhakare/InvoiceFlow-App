from django.contrib import admin
from .models import NotificationLog
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'event_type', 'delivery_status', 'recipient_email', 'timestamp')
    list_filter = ('event_type', 'delivery_status')
    search_fields = ('invoice__invoice_number', 'recipient_email')
    readonly_fields = ('timestamp',)
admin.site.register(NotificationLog, NotificationLogAdmin)