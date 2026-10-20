@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

fltmc >nul 2>nul
if errorlevel 1 (
    echo OpenMoxie needs administrator permission to add local-network firewall rules.
    powershell -NoProfile -Command "$p=Start-Process -FilePath '%~f0' -Verb RunAs -Wait -PassThru; exit $p.ExitCode"
    exit /b !errorlevel!
)

echo Configuring Windows Firewall for Moxie on the local subnet only...
netsh advfirewall firewall delete rule name="OpenMoxie MQTT from local network" >nul 2>nul
netsh advfirewall firewall add rule name="OpenMoxie MQTT from local network" dir=in action=allow protocol=TCP localport=8883 remoteip=LocalSubnet profile=private,public
if errorlevel 1 goto :failed

netsh advfirewall firewall delete rule name="OpenMoxie Vision from local network" >nul 2>nul
netsh advfirewall firewall add rule name="OpenMoxie Vision from local network" dir=in action=allow protocol=TCP localport=443 remoteip=LocalSubnet profile=private,public
if errorlevel 1 goto :failed

echo.
echo Local-network access is enabled for MQTT 8883 and optional Vision 443.
echo These rules do not allow Internet-wide access.
pause
exit /b 0

:failed
echo.
echo Windows Firewall could not be configured. Check administrator permissions.
pause
exit /b 1
