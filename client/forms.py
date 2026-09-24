from django import forms
from routers.models import Router

class RouterForm(forms.ModelForm):
    api_username = forms.CharField(label='MikroTik Username', required=True, initial='admin')
    api_password = forms.CharField(label='MikroTik Password', required=True, widget=forms.PasswordInput)
    router_os_version = forms.ChoiceField(label='RouterOS Version', choices=Router.ROUTER_OS_CHOICES, required=True)
    has_public_ip = forms.BooleanField(label='Router has a public IP?', required=False)

    class Meta:
        model = Router
        fields = ['name', 'api_username', 'api_password', 'router_os_version', 'has_public_ip']