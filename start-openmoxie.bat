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

call "%~dp0ensure-lm-studio-model.bat"
if errorlevel 1 (
    echo OpenMoxie was not started because LM Studio is not ready.
    pause
    exit /b 1
)

echo Starting OpenMoxie without Vision using existing images...
docker compose -f docker-compose.yml up -d --no-build --remove-orphans
if errorlevel 1 goto :start_failed

call :wait_for_server
if errorlevel 1 exit /b 1

call "%~dp0ensure-openmoxie-address.bat"
set "ADDRESS_CHECK_RESULT=%errorlevel%"
if "%ADDRESS_CHECK_RESULT%"=="1" exit /b 1

call :check_lm_from_docker
if errorlevel 1 exit /b 1

docker compose -f docker-compose.yml exec -T server python site/manage.py shell -c "from hive.models import HiveConfiguration; c=HiveConfiguration.objects.filter(name='default').first(); c and setattr(c, 'vision_extension_enabled', False); c and c.save(update_fields=['vision_extension_enabled'])" >nul 2>nul

docker compose -f docker-compose.yml ps
echo.
echo OpenMoxie is ready without Vision at http://localhost:8001/hive
call :report_robot_connection
if "%ADDRESS_CHECK_RESULT%"=="2" (
    echo Opening the new Migration QR because this computer's address changed.
    start "" "http://localhost:8001/hive/endpoint/"
) else (
    start "" "http://localhost:8001/hive"
)
exit /b 0

:not_built
echo.
echo OpenMoxie without Vision has not been built for tag %OPENMOXIE_VERSION%.
echo Run build-openmoxie.bat once, then run this starter again.
pause
exit /b 2

:start_failed
echo OpenMoxie did not start successfully. Recent logs:
docker compose -f docker-compose.yml logs --tail 40 server mqtt
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
powershell -NoProfile -Command "if(Get-NetFirewallRule -DisplayName 'OpenMoxie MQTT from local network' -ErrorAction SilentlyContinue){exit 0}else{exit 1}"
if errorlevel 1 (
    echo OpenMoxie's local-network firewall rule is missing.
    echo A Windows administrator prompt will open once to allow Moxie to connect.
    call "%~dp0setup-openmoxie-network.bat"
    if errorlevel 1 (
        echo Firewall setup was cancelled or failed. Moxie may remain at the OpenMoxie QR screen.
        pause
        exit /b 1
    )
)
exit /b 0

:wait_for_server
echo Waiting for OpenMoxie to finish database setup...
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){& curl.exe -fsS --max-time 3 -o NUL http://localhost:8001/hive/; if($LASTEXITCODE -eq 0){exit 0}; Start-Sleep -Seconds 2}; exit 1"
if errorlevel 1 (
    echo OpenMoxie started but the web page is not ready. Recent server logs:
    docker compose -f docker-compose.yml logs --tail 40 server
    pause
    exit /b 1
)
exit /b 0

:report_robot_connection
powershell -NoProfile -Command "try{$s=Invoke-RestMethod -TimeoutSec 8 http://localhost:8001/hive/connection_status; if(@($s.connected_devices).Count -gt 0){Write-Host ('Moxie connected: '+(@($s.connected_devices) -join ', '))}else{Write-Host 'Moxie is not connected yet. If she was off overnight, wake or reboot her and rescan Migration QR.'}}catch{Write-Host 'OpenMoxie is ready, but robot connection status was not available yet.'}"
exit /b 0

:check_lm_from_docker
docker compose -f docker-compose.yml exec -T server python -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://host.docker.internal:1234/v1/models',timeout=8)); assert any(x.get('id')=='qwen_qwen3.5-9b.gguf' for x in data.get('data',[])); print('LM Studio connection verified')"
if errorlevel 1 (
    echo OpenMoxie is running, but its container cannot reach the required LM Studio model.
    echo Allow LM Studio on Private networks in Windows Firewall, then run this starter again.
    pause
    exit /b 1
)
exit /b 0
