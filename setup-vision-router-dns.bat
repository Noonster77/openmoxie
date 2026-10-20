@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

for /f "usebackq tokens=1,2 delims=|" %%I in (`powershell -NoProfile -Command "$r=Get-NetRoute -DestinationPrefix '0.0.0.0/0' ^| Where-Object NextHop -ne '0.0.0.0' ^| Sort-Object RouteMetric,InterfaceMetric ^| Select-Object -First 1; if($r){$ip=Get-NetIPAddress -InterfaceIndex $r.InterfaceIndex -AddressFamily IPv4 ^| Where-Object {$_.IPAddress -notlike '169.254.*'} ^| Select-Object -First 1 -ExpandProperty IPAddress; Write-Output ($ip+'|'+$r.NextHop)}"`) do (
    set "VISION_HOST_IP=%%I"
    set "ROUTER_IP=%%J"
)

if not defined VISION_HOST_IP (
    echo Could not determine this computer's LAN address and router.
    echo Connect this computer to Moxie's home network, then run this file again.
    pause
    exit /b 1
)

echo OpenMoxie Vision router DNS setup
echo ==================================
echo OpenMoxie PC: %VISION_HOST_IP%
echo Router:       %ROUTER_IP%
echo.
echo The Migration QR cannot include a DNS server or hostname override.
echo A Windows hosts-file entry affects this PC only and will not be changed.
echo.
echo In the router, look for Local DNS, DNS Rules, DNS Proxy, Host Mapping,
echo or Address Records. Add BOTH exact A records:
echo.
echo   production-ic-worker.embodied.com  = %VISION_HOST_IP%
echo   staging-ic-worker.embodied.com     = %VISION_HOST_IP%
echo.
echo If the router has a DNS Proxy switch, enable it and make the router
echo ^(%ROUTER_IP%^) the DHCP DNS server. Remove public DNS as a DHCP fallback;
echo otherwise Moxie can bypass the local record. Do not change WAN DNS.
echo Reserve %VISION_HOST_IP% for this PC so the address does not move.
echo.
powershell -NoProfile -Command "$t='production-ic-worker.embodied.com = %VISION_HOST_IP%`r`nstaging-ic-worker.embodied.com = %VISION_HOST_IP%'; Set-Clipboard -Value $t" >nul 2>nul
echo The two records were copied to the clipboard.
echo Opening the router admin page now. Sign in and save the DNS/DHCP changes.
start "" "http://%ROUTER_IP%/"
echo.
pause

echo Verifying the router's DNS answers...
powershell -NoProfile -Command "$want='%VISION_HOST_IP%'; $server='%ROUTER_IP%'; $names=@('production-ic-worker.embodied.com','staging-ic-worker.embodied.com'); $ok=$true; foreach($n in $names){try{$a=@(Resolve-DnsName $n -Server $server -Type A -DnsOnly -ErrorAction Stop ^| Where-Object Type -eq A ^| ForEach-Object IPAddress); Write-Host ($n+' -> '+($a -join ', ')); if($a -notcontains $want){$ok=$false}}catch{Write-Host ($n+' -> no DNS answer from router');$ok=$false}}; if($ok){exit 0}else{exit 1}"
if errorlevel 1 goto :pending

echo.
echo SUCCESS: the router returns both Vision names as %VISION_HOST_IP%.
echo Power-cycle Moxie once to clear its old DNS cache, then start Vision.
pause
exit /b 0

:pending
echo.
echo The redirect is not active yet. No PC DNS or hosts settings were changed.
echo Some TP-Link firmware puts this under Services ^> DNS Proxy ^> DNS Rules;
echo other models require a Pi-hole, AdGuard Home, or another LAN DNS server.
echo After the records work, rerun this BAT to verify them.
pause
exit /b 2
