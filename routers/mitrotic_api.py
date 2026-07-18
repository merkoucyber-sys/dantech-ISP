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