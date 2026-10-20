@echo off
setlocal
cd /d "%~dp0"

set "MODEL_REPO=https://huggingface.co/Manojb/Qwen3.5-9B-Q4_K_S.gguf"
set "MODEL_SEARCH=Manojb/Qwen3.5-9B-Q4_K_S.gguf"
set "MODEL_ID=qwen_qwen3.5-9b.gguf"
set "CONTEXT_LENGTH=32768"

where lms >nul 2>nul
if errorlevel 1 (
    if exist "%USERPROFILE%\.cache\lm-studio\bin\lms.exe" (
        set "LMS=%USERPROFILE%\.cache\lm-studio\bin\lms.exe"
    ) else if exist "%USERPROFILE%\.lmstudio\bin\lms.exe" (
        set "LMS=%USERPROFILE%\.lmstudio\bin\lms.exe"
    ) else (
        echo LM Studio's lms command was not found.
        echo Install and open LM Studio once, then run this file again.
        echo https://lmstudio.ai/
        pause
        exit /b 1
    )
) else (
    set "LMS=lms"
)

echo.
echo Recommended everyday model: Qwen3.5 9B Q4_K_S
echo Approximate download: 6.5 GB. Make sure you have enough disk space.
echo.

"%LMS%" ls | findstr /i /c:"qwen3.5-9b" /c:"qwen_qwen3.5-9b" >nul
if errorlevel 1 (
    echo Downloading the Q4_K_S model through LM Studio...
    "%LMS%" get "%MODEL_REPO%" --gguf -y
    if errorlevel 1 (
        echo Automatic download failed. Open LM Studio and search for:
        echo Manojb/Qwen3.5-9B-Q4_K_S.gguf
        pause
        exit /b 1
    )
) else (
    echo The Qwen3.5 9B model is already in LM Studio.
)

echo Loading the model with a stable API identifier...
"%LMS%" load "%MODEL_SEARCH%" --context-length %CONTEXT_LENGTH% --identifier "%MODEL_ID%" -y
if errorlevel 1 (
    echo The exact repository name did not resolve. Trying the local model identifier...
    "%LMS%" load "%MODEL_ID%" --context-length %CONTEXT_LENGTH% --identifier "%MODEL_ID%" -y
)
if errorlevel 1 (
    echo LM Studio could not load the model. Check its resource estimate and guardrails.
    "%LMS%" load "%MODEL_SEARCH%" --context-length %CONTEXT_LENGTH% --estimate-only
    pause
    exit /b 1
)

echo Ensuring the LM Studio background daemon is running...
"%LMS%" daemon up >nul 2>nul

rem A running listener may still be bound only to 127.0.0.1. Status does not
rem report its bind address, so restart it explicitly with Docker-accessible
rem settings every time this setup script runs.
"%LMS%" server stop >nul 2>nul
echo Starting the LM Studio API listener on 0.0.0.0:1234...
echo Keep Windows Firewall access limited to Private networks.
"%LMS%" server start --port 1234 --bind 0.0.0.0
if errorlevel 1 (
    echo The model loaded, but the API server did not start.
    pause
    exit /b 1
)

powershell -NoProfile -Command "$s=Get-NetTCPConnection -LocalPort 1234 -State Listen -ErrorAction SilentlyContinue ^| Select-Object -First 1; if(-not $s -or $s.LocalAddress -notin @('0.0.0.0','::')){exit 1}; try{$r=Invoke-RestMethod -TimeoutSec 5 http://127.0.0.1:1234/v1/models; if($r.data){exit 0}}catch{}; exit 1"
if errorlevel 1 (
    echo LM Studio did not expose a verified network listener on port 1234.
    echo Open LM Studio Developer settings, enable serving on the local network, and run this file again.
    pause
    exit /b 1
)

docker compose ps --status running --services 2>nul | findstr /x "server" >nul
if not errorlevel 1 (
    echo Verifying that the OpenMoxie Docker container can reach LM Studio...
    docker compose exec -T server python -c "import urllib.request; urllib.request.urlopen('http://host.docker.internal:1234/v1/models',timeout=8).read(); print('Docker-to-LM-Studio connection verified')"
    if errorlevel 1 (
        echo LM Studio works on Windows, but Docker cannot reach it. Check Private-network firewall access.
        pause
        exit /b 1
    )
)

echo.
echo LM Studio is ready. Use these OpenMoxie Setup values:
echo   Chat provider: LM Studio (local)
echo   Model identifier: %MODEL_ID%
echo   API base URL: http://host.docker.internal:1234/v1
echo   Speech provider: Local faster-whisper
echo.
"%LMS%" ps
start "" "http://localhost:8001/hive/setup"
pause
endlocal
