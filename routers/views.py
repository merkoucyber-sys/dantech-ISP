from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from .models import Router
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

    online_cutoff = timezone.now() - timedelta(minutes=5)
    for router in routers:
        status = 'online' if router.last_seen and router.last_seen >= online_cutoff else 'offline'
        users = []

        router_data.append({
            'id': router.id,
            'name': router.name,
            'status': status,
            'users': users,
            'ip': router.ip_address,
            'connection_token': router.connection_token,
        })

    return render(request, 'routers/dashboard.html', {'routers': router_data})


@login_required(login_url='/accounts/login/')
def delete_router(request, router_id):
    if request.method != 'POST':
        return HttpResponse('POST required', status=405)

    router = Router.objects.filter(id=router_id).first()
    if not router or (not request.user.is_superuser and router.client.user_id != request.user.id):
        return HttpResponse('Router not found', status=404)

    router.delete()
    return redirect('dashboard')


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


@login_required(login_url='/accounts/login/')
def router_script(request, router_id):
    router = Router.objects.filter(id=router_id).first()
    if not router or (not request.user.is_superuser and router.client.user_id != request.user.id):
        return HttpResponse('Router not found', status=404)

    base_url = getattr(settings, 'PUBLIC_BASE_URL', '').rstrip('/')
    if not base_url:
        base_url = request.build_absolute_uri('/').rstrip('/')
    heartbeat_url = f'{base_url}/routers/heartbeat/{router.connection_token}/'
    router_name = router.name.replace('"', '').replace('\n', ' ').strip()
    has_public_ip = 'yes' if router.has_public_ip else 'no'
    script = f'''# Netcore ISP all-in-one MikroTik setup
# Router: {router_name}
# RouterOS profile: {router.router_os_version}
# Public IP configured: {has_public_ip}
# Paste this complete file into WinBox -> Terminal on a fresh router.
# BACK UP an existing router before running this script.
# Layout: ether1 = WAN, ether2-ether5 = hotspot/customer LAN.
# WAN assumption: the ISP gives ether1 an address by DHCP.

/system identity set name="{router_name}"

# WAN: receive the internet connection on ether1.
:if ([:len [/ip dhcp-client find interface="ether1"]] = 0) do={{
    /ip dhcp-client add interface="ether1" add-default-route=yes use-peer-dns=yes disabled=no comment="Netcore WAN"
}}

# LAN: put ether2-ether5 into one customer bridge.
:if ([:len [/interface bridge find name="netcore-hotspot"]] = 0) do={{
    /interface bridge add name="netcore-hotspot" protocol-mode=rstp comment="Netcore hotspot LAN"
}}
:foreach lanPort in={{"ether2";"ether3";"ether4";"ether5"}} do={{
    :if ([:len [/interface find name=$lanPort]] > 0) do={{
        :if ([:len [/interface bridge port find bridge="netcore-hotspot" interface=$lanPort]] = 0) do={{
            /interface bridge port add bridge="netcore-hotspot" interface=$lanPort
        }}
    }}
}}

# LAN gateway and DHCP service.
:if ([:len [/ip address find address="10.10.10.1/24" interface="netcore-hotspot"]] = 0) do={{
    /ip address add address=10.10.10.1/24 interface="netcore-hotspot" comment="Netcore hotspot gateway"
}}
:if ([:len [/ip pool find name="netcore-hotspot-pool"]] = 0) do={{
    /ip pool add name="netcore-hotspot-pool" ranges=10.10.10.10-10.10.10.254
}}
:if ([:len [/ip dhcp-server find name="netcore-hotspot-dhcp"]] = 0) do={{
    /ip dhcp-server add name="netcore-hotspot-dhcp" interface="netcore-hotspot" address-pool="netcore-hotspot-pool" lease-time=1h disabled=no
}}
:if ([:len [/ip dhcp-server network find address="10.10.10.0/24"]] = 0) do={{
    /ip dhcp-server network add address=10.10.10.0/24 gateway=10.10.10.1 dns-server=10.10.10.1 comment="Netcore hotspot network"
}}
/ip dns set allow-remote-requests=yes

# NAT: allow hotspot customers to reach the internet through ether1.
:if ([:len [/ip firewall nat find comment="Netcore hotspot masquerade"]] = 0) do={{
    /ip firewall nat add chain=srcnat out-interface="ether1" action=masquerade comment="Netcore hotspot masquerade"
}}

# MikroTik captive hotspot service on the customer bridge.
:if ([:len [/ip hotspot server find name="netcore-hotspot"]] = 0) do={{
    /ip hotspot profile add name="netcore-hotspot-profile" hotspot-address=10.10.10.1 dns-name="wifi.danatech.co.ke" login-by=http-chap,http-pap
    /ip hotspot add name="netcore-hotspot" interface="netcore-hotspot" address-pool="netcore-hotspot-pool" profile="netcore-hotspot-profile" disabled=no
}}

# Keep the router registered with Netcore through its outbound HTTPS connection.
:if ([:len [/system script find name="netcore-heartbeat"]] > 0) do={{
    /system script remove [find name="netcore-heartbeat"]
}}
/system script add name="netcore-heartbeat" policy=read,write,test source={{
    :local netcoreUrl "{heartbeat_url}"
    :local identity [/system identity get name]
    :local serial "unknown"
    :do {{ :set serial [/system routerboard get serial-number] }} on-error={{}}
    :local payload ("identity=" . $identity . "&serial=" . $serial)
    /tool fetch url=$netcoreUrl http-method=post http-data=$payload output=none keep-result=no
}}

:if ([:len [/system scheduler find name="netcore-heartbeat"]] > 0) do={{
    /system scheduler remove [find name="netcore-heartbeat"]
}}
/system scheduler add name="netcore-heartbeat" interval=1m start-time=startup on-event="/system script run netcore-heartbeat"
/system script run netcore-heartbeat
:log info "Netcore ISP router connected"
'''
    response = HttpResponse(script, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{router.name}-netcore.rsc"'
    return response


@csrf_exempt
def router_heartbeat(request, token):
    if request.method != 'POST':
        return JsonResponse({'detail': 'POST required'}, status=405)
    router = Router.objects.filter(connection_token=token).first()
    if not router:
        return JsonResponse({'detail': 'Invalid connection token'}, status=404)
    router.last_seen = timezone.now()
    router.status = 'online'
    router.ip_address = request.META.get('REMOTE_ADDR') or router.ip_address
    router.save(update_fields=['last_seen', 'status', 'ip_address'])
    return JsonResponse({'ok': True})