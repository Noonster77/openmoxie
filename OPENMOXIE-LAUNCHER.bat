@echo off
setlocal EnableExtensions
cd /d "%~dp0"

:menu
cls
echo ==============================================================
echo                    OpenMoxie Launcher
echo ==============================================================
echo.
echo FIRST TIME on this computer:
echo   [1] Build and start OpenMoxie without Vision
echo   [2] Build and start OpenMoxie with Vision
echo.
echo FUTURE LAUNCHES - these never rebuild:
echo   [3] Start OpenMoxie without Vision
echo   [4] Start OpenMoxie with Vision
echo.
echo VISION NETWORK SETUP:
echo   [5] Configure or verify the router DNS redirect
echo.
echo   [Q] Quit
echo.
echo The start options automatically check Docker, LM Studio,
echo the qwen_qwen3.5-9b.gguf model, firewall access, and connection.
echo The first model download is approximately 6.5 GB.
echo.
choice /c 12345Q /n /m "Choose 1, 2, 3, 4, 5, or Q: "

if errorlevel 6 exit /b 0
if errorlevel 5 goto :dns
if errorlevel 4 goto :start_vision
if errorlevel 3 goto :start_standard
if errorlevel 2 goto :first_vision
if errorlevel 1 goto :first_standard

:first_standard
call "%~dp0build-openmoxie.bat"
if errorlevel 1 goto :failed
call "%~dp0start-openmoxie.bat"
goto :done

:first_vision
echo.
echo Vision requires two internal DNS records in your router, Pi-hole,
echo AdGuard Home, or another local DNS server. A Windows hosts entry
echo does not work for Moxie itself.
echo Your router's DHCP settings must give that local DNS server to Moxie
echo when the robot joins Wi-Fi; do not leave public DNS as a fallback.
choice /c YN /n /m "Do you know how to configure that internal DNS redirect? [Y/N]: "
if errorlevel 2 (
    echo.
    echo No problem. Installing ordinary OpenMoxie without Vision instead.
    echo You can return to Vision later when the DNS redirect is ready.
    goto :first_standard
)
call "%~dp0build-openmoxie-vision.bat"
if errorlevel 1 goto :failed
set "OPENMOXIE_VISION_DNS_READY=1"
call "%~dp0start-openmoxie-vision.bat"
set "VISION_START_RESULT=%errorlevel%"
set "OPENMOXIE_VISION_DNS_READY="
if not "%VISION_START_RESULT%"=="0" goto :failed
echo.
echo Vision is running on the computer. When you are ready to connect
echo Moxie's camera, choose option 5 to configure the router DNS redirect.
goto :done

:start_standard
call "%~dp0start-openmoxie.bat"
if errorlevel 1 goto :failed
goto :done

:start_vision
echo.
choice /c YN /n /m "Is local DNS configured and advertised to Moxie by DHCP? [Y/N]: "
if errorlevel 2 (
    echo Starting ordinary OpenMoxie without Vision instead.
    goto :start_standard
)
set "OPENMOXIE_VISION_DNS_READY=1"
call "%~dp0start-openmoxie-vision.bat"
set "VISION_START_RESULT=%errorlevel%"
set "OPENMOXIE_VISION_DNS_READY="
if not "%VISION_START_RESULT%"=="0" goto :failed
goto :done

:dns
call "%~dp0setup-vision-router-dns.bat"
goto :done

:failed
echo.
echo Setup did not finish. Read the message above, correct that item,
echo and run OPENMOXIE-LAUNCHER.bat again.

:done
echo.
pause
goto :menu
