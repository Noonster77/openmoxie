@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$r=Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Where-Object NextHop -ne '0.0.0.0' | Sort-Object RouteMetric,InterfaceMetric | Select-Object -First 1; if($r){Get-NetIPAddress -InterfaceIndex $r.InterfaceIndex -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '169.254.*'} | Select-Object -First 1 -ExpandProperty IPAddress}"`) do set "CURRENT_LAN_IP=%%I"
if not defined CURRENT_LAN_IP (
    echo Could not determine this computer's current LAN address.
    exit /b 1
)

for /f "usebackq delims=" %%I in (`docker compose -f docker-compose.yml exec -T server python site/manage.py shell -c "from hive.models import HiveConfiguration; c=HiveConfiguration.objects.filter(name='default').first(); print(c.external_host if c else '')" 2^>nul`) do set "SAVED_MQTT_HOST=%%I"

if "!SAVED_MQTT_HOST!"=="!CURRENT_LAN_IP!" (
    echo OpenMoxie LAN address is still !CURRENT_LAN_IP!.
    exit /b 0
)

if not defined SAVED_MQTT_HOST goto :update_address
if "!SAVED_MQTT_HOST:~0,3!"=="10." goto :update_address
if "!SAVED_MQTT_HOST:~0,8!"=="192.168." goto :update_address
if "!SAVED_MQTT_HOST:~0,4!"=="172." goto :update_address

echo OpenMoxie uses the custom MQTT host !SAVED_MQTT_HOST!.
echo It was not replaced with the detected LAN address !CURRENT_LAN_IP!.
exit /b 0

:update_address
echo This computer's LAN address changed from !SAVED_MQTT_HOST! to !CURRENT_LAN_IP!.
docker compose -f docker-compose.yml exec -T server python site/manage.py shell -c "from hive.models import HiveConfiguration; c=HiveConfiguration.objects.filter(name='default').first(); assert c, 'Complete OpenMoxie Setup first'; c.external_host='!CURRENT_LAN_IP!'; c.save(update_fields=['external_host'])" >nul
if errorlevel 1 (
    echo OpenMoxie could not save the new LAN address.
    exit /b 1
)

echo The Migration QR was updated. Show the new Migration QR to Moxie.
echo Reserve !CURRENT_LAN_IP! for this PC in router DHCP to prevent this recurring.
exit /b 2
