from django.contrib import admin
from .models import PppoeUser, RadiusSession, WifiUser, WifiUserDevice

admin.site.register(WifiUser)
admin.site.register(WifiUserDevice)
admin.site.register(PppoeUser)
admin.site.register(RadiusSession)
