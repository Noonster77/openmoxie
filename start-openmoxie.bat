@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found. Start Docker Desktop, then run this file again.
    pause
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo Docker Desktop is not ready. Start it, wait for it to finish loading, then run this file again.
    pause
    exit /b 1
)

echo Starting OpenMoxie...
docker compose up --build -d --remove-orphans
if errorlevel 1 (
    echo OpenMoxie did not start successfully.
    pause
    exit /b 1
)

docker compose ps
echo.
echo Waiting for OpenMoxie to finish database setup...
powershell -NoProfile -Command "$u='http://localhost:8001/hive'; for($i=0;$i -lt 60;$i++){try{$null=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $u; exit 0}catch{Start-Sleep -Seconds 2}}; exit 1"
if errorlevel 1 (
    echo OpenMoxie started but the web page is not ready. Recent server logs:
    docker compose logs --tail 40 server
    pause
    exit /b 1
)

echo OpenMoxie is ready at http://localhost:8001/hive
start "" "http://localhost:8001/hive"
endlocal
