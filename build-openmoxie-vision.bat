@echo off
setlocal EnableExtensions
cd /d "%~dp0"

call :check_docker
if errorlevel 1 exit /b 1

if not defined OPENMOXIE_VERSION set "OPENMOXIE_VERSION=latest"
if not exist "local\work\vision" mkdir "local\work\vision"

echo Checking for existing OpenMoxie Vision images...
call :show_image "openmoxie/openmoxie-mqtt:%OPENMOXIE_VERSION%"
call :show_image "openmoxie/openmoxie-server:%OPENMOXIE_VERSION%"
call :show_image "openmoxie-vision:latest"
echo.
echo Building OpenMoxie with Vision. Docker will reuse its build cache.
docker compose -f docker-compose.yml -f docker-compose.vision.yml build mqtt server vision
if errorlevel 1 (
    echo.
    echo OpenMoxie Vision build failed.
    pause
    exit /b 1
)

echo.
echo OpenMoxie with Vision is built successfully.
echo Run start-openmoxie-vision.bat to start it without rebuilding.
exit /b 0

:check_docker
where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found. Install or start Docker Desktop, then run this file again.
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

:show_image
docker image inspect %~1 --format "  %~1 already exists - built {{.Created}}" 2>nul
if errorlevel 1 echo   %~1 is not built yet.
exit /b 0
