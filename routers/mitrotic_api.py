try:
    from librouteros import connect
except ImportError:
    connect = None

from django.shortcuts import render, redirect
from client.forms import RouterForm
from .models import Router

def register_router(request):
    if request.method == 'POST':
        form = RouterForm(request.POST)
        if form.is_valid():
            router = form.save(commit=False)
            router.client = request.user.client  # link to logged-in client
            router.save()
            return redirect('dashboard')
    else:
        form = RouterForm()
    return render(request, 'routers/register_router.html', {'form': form})

def get_router_status(ip, username, password):
    if connect is None:
        return [], 'offline'

    try:
        api = connect(username=username, password=password, host=ip)
        users = list(api('/ip/hotspot/active'))  # active users
        return users, 'online'
    except:
        return [], 'offline'


def enforce_wifi_account(router, wifi_user):
    """Create or update a MikroTik hotspot account with one-device access."""
    if connect is None:
        return False, 'librouteros is not installed'
    if not router.api_username or not router.api_password or not wifi_user.device_mac:
        return False, 'Router credentials or device MAC is missing'

    try:
        api = connect(
            username=router.api_username,
            password=router.api_password,
            host=router.ip_address,
        )
        users = api.get_resource('/ip/hotspot/user')
        existing_users = list(users.get(name=wifi_user.username))
        fields = {
            'name': wifi_user.username,
            'password': wifi_user.password,
            'mac-address': wifi_user.device_mac,
            'shared-users': '1',
        }

        if existing_users:
            users.set(id=existing_users[0]['id'], **fields)
        else:
            users.add(**fields)
        return True, 'enforced'
    except Exception as error:
        return False, str(error)


def enforce_wifi_account_on_client_routers(wifi_user):
    """Apply one-device hotspot enforcement to every configured client router."""
    routers = list(wifi_user.client.routers.all())
    if not routers:
        return True, []

    results = []
    all_successful = True
    for router in routers:
        success, message = enforce_wifi_account(router, wifi_user)
        results.append((router, success, message))
        all_successful = all_successful and success
    return all_successful, results