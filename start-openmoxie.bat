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
docker compose up -d --remove-orphans
if errorlevel 1 (
    echo OpenMoxie did not start successfully.
    pause
    exit /b 1
)

docker compose ps
echo.
echo OpenMoxie is available at http://localhost:8001/hive
start "" "http://localhost:8001/hive"
endlocal
