from django import forms
from routers.models import Router

class RouterForm(forms.ModelForm):
    class Meta:
        model = Router
        fields = ['name', 'ip_address', 'api_username', 'api_password', 'latitude', 'longitude']