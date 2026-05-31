from django.contrib import admin
from .models import Invoice, LineItem

admin.site.register(Invoice)

class LineItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'invoice', 'get_service_name', 'total_hours')
    list_filter = ('invoice',)

    def get_service_name(self, obj):
        if obj.services:
            return obj.services.name
        return '[No Service Attached]'
    get_service_name.short_description = 'Service Name'

admin.site.register(LineItem, LineItemAdmin)
