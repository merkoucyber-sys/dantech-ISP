from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # ✅ Use actual fields from your Client model
    list_display = ('name', 'phone', 'instructions')
    search_fields = ('name', 'phone')
    list_filter = ('name',)  # Example filter, adjust as needed