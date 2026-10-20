@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found. Install and start Docker Desktop, then run this file again.
    pause
    exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
    echo Docker Desktop is not ready. Start it and wait for the engine to finish loading.
    pause
    exit /b 1
)

echo Vision requires an internal DNS redirect configured in your router,
echo Pi-hole, AdGuard Home, or another local DNS server.
echo Your Wi-Fi router must advertise that DNS server to Moxie through DHCP.
choice /c YN /n /m "Do you know how to configure that internal DNS/DHCP redirect? [Y/N]: "
if errorlevel 2 (
    echo.
    echo No problem. Installing ordinary OpenMoxie without Vision instead.
    call "%~dp0build-openmoxie.bat"
    if errorlevel 1 exit /b 1
    call "%~dp0start-openmoxie.bat"
    if errorlevel 1 exit /b 1
    exit /b 0
)

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$ip=(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object {$_.IPAddress -notlike '127.*' -and $_.InterfaceAlias -notmatch 'vEthernet|Docker|WSL'} ^| Sort-Object InterfaceMetric ^| Select-Object -First 1 -ExpandProperty IPAddress); if($ip){$ip}"`) do set "VISION_HOST_IP=%%I"
if not defined VISION_HOST_IP (
    echo Could not determine this computer's LAN address.
    echo Connect to the home network and run this file again.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$owner=Get-NetTCPConnection -LocalPort 443 -State Listen -ErrorAction SilentlyContinue ^| Select-Object -First 1; if($owner){$owner.OwningProcess}"`) do set "PORT443_PID=%%I"
if defined PORT443_PID (
    docker inspect openmoxie-vision >nul 2>nul
    if errorlevel 1 (
        echo Port 443 is already used by process %PORT443_PID%.
        echo Stop that HTTPS service before installing Moxie Vision.
        pause
        exit /b 1
    )
)

if not exist "local\work\vision" mkdir "local\work\vision"

echo Building OpenMoxie Vision. The first build downloads the local detector dependencies.
call "%~dp0build-openmoxie-vision.bat"
if errorlevel 1 (
    echo Vision images did not build.
    pause
    exit /b 1
)

echo Starting the existing Vision images without rebuilding...
docker compose -f docker-compose.yml -f docker-compose.vision.yml up -d --no-build --remove-orphans
if errorlevel 1 (
    echo Vision containers did not start. Recent logs:
    docker compose -f docker-compose.yml -f docker-compose.vision.yml logs --tail 80 server mqtt vision
    pause
    exit /b 1
)

echo Waiting for the detector and HTTPS receiver...
rem curl.exe handles the receiver's intentionally self-signed LAN certificate
rem consistently across Windows PowerShell 5.1 and newer PowerShell releases.
powershell -NoProfile -Command "for($i=0;$i -lt 120;$i++){try{$json=(& curl.exe -ksSf --max-time 3 https://localhost/health); if($LASTEXITCODE -eq 0){$r=ConvertFrom-Json -InputObject $json; if($r.ready -and $r.model_loaded){exit 0}}}catch{}; Start-Sleep -Seconds 2}; exit 1"
if errorlevel 1 (
    echo Vision did not become ready. Recent logs:
    docker compose -f docker-compose.yml -f docker-compose.vision.yml logs --tail 80 vision
    pause
    exit /b 1
)

docker compose -f docker-compose.yml -f docker-compose.vision.yml exec -T server python site/manage.py shell -c "from hive.models import HiveConfiguration; c=HiveConfiguration.objects.filter(name='default').first(); assert c, 'Complete the base OpenMoxie Setup page first'; c.vision_extension_enabled=True; c.save(update_fields=['vision_extension_enabled']); print('Vision controls enabled in OpenMoxie')"
if errorlevel 1 (
    echo Vision is running, but base OpenMoxie setup is not complete.
    echo Complete the Setup page, then run setup-vision.bat again.
    pause
    exit /b 1
)

>"local\work\vision-enabled.flag" echo Optional vision overlay installed.

echo.
echo OpenMoxie Vision is installed at https://%VISION_HOST_IP%/api/v1/caption
echo.
echo REQUIRED ROUTER OR LOCAL-DNS OVERRIDES:
echo   production-ic-worker.embodied.com  -^> %VISION_HOST_IP%
echo   staging-ic-worker.embodied.com     -^> %VISION_HOST_IP%
echo.
echo Configure these in your router, Pi-hole, AdGuard Home, or local DNS server.
echo A Windows hosts-file entry does NOT redirect Moxie itself.
echo The Migration QR cannot carry a DNS override either.
echo.
echo Opening the guided router setup and DNS verifier...
call "%~dp0setup-vision-router-dns.bat"
echo.
echo Then open Setup, start Vision, and choose Vision or I Spy for the robot.
start "" "http://localhost:8001/hive/setup"
pause
endlocal
