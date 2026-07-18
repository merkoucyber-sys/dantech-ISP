from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Router
from .mitrotic_api import get_router_status
from accounts.models import Client

@login_required(login_url='/accounts/login/')
def dashboard(request):

    # ✅ SUPERUSER → see all routers
    if request.user.is_superuser:
        routers = Router.objects.all()

    else:
        # ✅ NORMAL USER → check if has client
        try:
            client = request.user.client
            routers = Router.objects.filter(client=client)
        except Client.DoesNotExist:
            return render(request, 'routers/no_client.html')  # show message page

    router_data = []

    for router in routers:
        try:
            users, status = get_router_status(
                router.ip_address,
                router.api_username,
                router.api_password
            )
        except:
            users = []
            status = 'offline'

        router.status = status
        router.save()

        router_data.append({
            'name': router.name,
            'status': status,
            'users': users,
            'latitude': router.latitude,
            'longitude': router.longitude,
            'ip': router.ip_address
        })

    return render(request, 'routers/dashboard.html', {'routers': router_data})
def register_router(request):
    from django.shortcuts import render, redirect
    from client.forms import RouterForm
    from accounts.models import Client

    if request.method == 'POST':
        form = RouterForm(request.POST)
        if form.is_valid():
            router = form.save(commit=False)

            if request.user.is_superuser:
                router.client = Client.objects.first()  # temporary
            else:
                router.client = request.user.client

            router.save()
            return redirect('dashboard')
    else:
        form = RouterForm()

    return render(request, 'routers/register_router.html', {'form': form})