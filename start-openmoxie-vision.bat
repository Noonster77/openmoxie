@echo off
setlocal EnableExtensions
cd /d "%~dp0"

call :check_docker
if errorlevel 1 exit /b 1
call :check_firewall
if errorlevel 1 exit /b 1

if not defined OPENMOXIE_VERSION set "OPENMOXIE_VERSION=latest"
docker image inspect "openmoxie/openmoxie-mqtt:%OPENMOXIE_VERSION%" >nul 2>nul
if errorlevel 1 goto :not_built
docker image inspect "openmoxie/openmoxie-server:%OPENMOXIE_VERSION%" >nul 2>nul
if errorlevel 1 goto :not_built
docker image inspect "openmoxie-vision:latest" >nul 2>nul
if errorlevel 1 goto :not_built

if "%OPENMOXIE_VISION_DNS_READY%"=="1" goto :dns_ready
echo.
echo Vision requires an internal DNS redirect configured in your router,
echo Pi-hole, AdGuard Home, or another local DNS server.
echo The Wi-Fi router must advertise that DNS server to Moxie through DHCP.
choice /c YN /n /m "Is that DNS/DHCP redirect configured, or do you know how to configure it? [Y/N]: "
if errorlevel 2 goto :use_standard

:dns_ready
call "%~dp0ensure-lm-studio-model.bat"
if errorlevel 1 (
    echo OpenMoxie Vision was not started because LM Studio is not ready.
    pause
    exit /b 1
)

if not exist "local\work\vision" mkdir "local\work\vision"
echo Starting OpenMoxie with Vision using existing images...
docker compose -f docker-compose.yml -f docker-compose.vision.yml up -d --no-build --remove-orphans
if errorlevel 1 goto :start_failed

call :wait_for_services
if errorlevel 1 exit /b 1

call "%~dp0ensure-openmoxie-address.bat"
set "ADDRESS_CHECK_RESULT=%errorlevel%"
if "%ADDRESS_CHECK_RESULT%"=="1" exit /b 1

call :check_lm_from_docker
if errorlevel 1 exit /b 1

docker compose -f docker-compose.yml -f docker-compose.vision.yml exec -T server python site/manage.py shell -c "from hive.models import HiveConfiguration; c=HiveConfiguration.objects.filter(name='default').first(); c and setattr(c, 'vision_extension_enabled', True); c and c.save(update_fields=['vision_extension_enabled'])" >nul 2>nul
>"local\work\vision-enabled.flag" echo Optional vision overlay installed.

docker compose -f docker-compose.yml -f docker-compose.vision.yml ps
echo.
echo OpenMoxie is ready with Vision:
echo   Dashboard: http://localhost:8001/hive
echo   Vision:    https://localhost/health
echo Moxie must receive the overriding local DNS server from Wi-Fi DHCP
echo before it can route its hard-coded Vision hostnames to this computer.
call :report_robot_connection
if "%ADDRESS_CHECK_RESULT%"=="2" (
    echo Opening the new Migration QR because this computer's address changed.
    start "" "http://localhost:8001/hive/endpoint/"
) else (
    start "" "http://localhost:8001/hive"
)
exit /b 0

:use_standard
echo.
echo Starting ordinary OpenMoxie without Vision instead.
echo You can add Vision later when its internal DNS redirect is ready.
call "%~dp0start-openmoxie.bat"
exit /b %errorlevel%

:not_built
echo.
echo OpenMoxie with Vision has not been completely built for tag %OPENMOXIE_VERSION%.
echo Run build-openmoxie-vision.bat once, then run this starter again.
pause
exit /b 2

:start_failed
echo OpenMoxie Vision did not start successfully. Recent logs:
docker compose -f docker-compose.yml -f docker-compose.vision.yml logs --tail 60 server mqtt vision
pause
exit /b 1

:check_docker
where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found. Start Docker Desktop, then run this file again.
    pause
    exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
    echo Docker Desktop is not ready. Start it and wait for the engine to finish loading.
    pause
    exit /b 1
)
exit /b 0

:check_firewall
powershell -NoProfile -Command "if((Get-NetFirewallRule -DisplayName 'OpenMoxie MQTT from local network' -ErrorAction SilentlyContinue) -and (Get-NetFirewallRule -DisplayName 'OpenMoxie Vision from local network' -ErrorAction SilentlyContinue)){exit 0}else{exit 1}"
if errorlevel 1 (
    echo OpenMoxie's local-network firewall rules are missing.
    echo A Windows administrator prompt will open once to allow Moxie to connect.
    call "%~dp0setup-openmoxie-network.bat"
    if errorlevel 1 (
        echo Firewall setup was cancelled or failed.
        pause
        exit /b 1
    )
)
exit /b 0

:wait_for_services
echo Waiting for OpenMoxie and the Vision detector...
powershell -NoProfile -Command "for($i=0;$i -lt 120;$i++){try{& curl.exe -fsS --max-time 3 -o NUL http://localhost:8001/hive/; if($LASTEXITCODE -eq 0){$json=& curl.exe -ksSf --max-time 3 https://localhost/health; if($LASTEXITCODE -eq 0){$v=ConvertFrom-Json -InputObject $json; if($v.ready -and $v.model_loaded){exit 0}}}}catch{}; Start-Sleep -Seconds 2}; exit 1"
if errorlevel 1 (
    echo OpenMoxie or Vision did not become ready. Recent logs:
    docker compose -f docker-compose.yml -f docker-compose.vision.yml logs --tail 60 server vision
    pause
    exit /b 1
)
exit /b 0

:report_robot_connection
powershell -NoProfile -Command "try{$s=Invoke-RestMethod -TimeoutSec 8 http://localhost:8001/hive/connection_status; if(@($s.connected_devices).Count -gt 0){Write-Host ('Moxie connected: '+(@($s.connected_devices) -join ', '))}else{Write-Host 'Moxie is not connected yet. If she was off overnight, wake or reboot her and rescan Migration QR.'}}catch{Write-Host 'OpenMoxie is ready, but robot connection status was not available yet.'}"
exit /b 0

:check_lm_from_docker
docker compose -f docker-compose.yml -f docker-compose.vision.yml exec -T server python -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://host.docker.internal:1234/v1/models',timeout=8)); assert any(x.get('id')=='qwen_qwen3.5-9b.gguf' for x in data.get('data',[])); print('LM Studio connection verified')"
if errorlevel 1 (
    echo OpenMoxie is running, but its container cannot reach the required LM Studio model.
    echo Allow LM Studio on Private networks in Windows Firewall, then run this starter again.
    pause
    exit /b 1
)
exit /b 0
