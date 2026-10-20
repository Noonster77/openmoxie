@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found.
    exit /b 1
)

set "OPENMOXIE_VERSION=latest"
echo Building and pushing '%OPENMOXIE_VERSION%'
docker compose -f docker-compose.yml build mqtt server || exit /b 1
docker compose -f docker-compose.yml push mqtt server || exit /b 1

set /p OPENMOXIE_VERSION=<site\VERSION
if not defined OPENMOXIE_VERSION (
    echo site\VERSION is empty.
    exit /b 1
)
echo Building and pushing '%OPENMOXIE_VERSION%'
docker compose -f docker-compose.yml build mqtt server || exit /b 1
docker compose -f docker-compose.yml push mqtt server || exit /b 1

endlocal
