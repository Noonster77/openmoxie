@echo off
setlocal EnableExtensions
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
        echo Install and open LM Studio once, then run setup-lm-studio-model.bat.
        exit /b 1
    )
) else (
    set "LMS=lms"
)

echo Checking LM Studio model and API...
"%LMS%" daemon up >nul 2>nul

"%LMS%" ps | findstr /i /c:"%MODEL_ID%" >nul
if errorlevel 1 (
    echo The required model is not loaded. Loading %MODEL_ID%...
    "%LMS%" ls | findstr /i /c:"qwen3.5-9b" /c:"qwen_qwen3.5-9b" >nul
    if errorlevel 1 (
        echo The required model is not installed. Downloading approximately 6.5 GB...
        "%LMS%" get "%MODEL_REPO%" --gguf -y
        if errorlevel 1 exit /b 1
    )

    "%LMS%" load "%MODEL_SEARCH%" --context-length %CONTEXT_LENGTH% --identifier "%MODEL_ID%" -y
    if errorlevel 1 "%LMS%" load "%MODEL_ID%" --context-length %CONTEXT_LENGTH% --identifier "%MODEL_ID%" -y
    if errorlevel 1 (
        echo LM Studio could not load %MODEL_ID%.
        exit /b 1
    )
)

netstat -ano -p TCP | findstr /c:"0.0.0.0:1234" >nul
if errorlevel 1 goto :restart_api
powershell -NoProfile -Command "try{$r=Invoke-RestMethod -TimeoutSec 5 http://127.0.0.1:1234/v1/models; if(@($r.data.id) -contains '%MODEL_ID%'){exit 0}}catch{}; exit 1"
if errorlevel 1 goto :restart_api
goto :verify_api

:restart_api
echo Starting the LM Studio API on 0.0.0.0:1234 for Docker access...
"%LMS%" server stop >nul 2>nul
"%LMS%" server start --port 1234 --bind 0.0.0.0
if errorlevel 1 (
    echo The LM Studio API server did not start.
    exit /b 1
)

:verify_api

powershell -NoProfile -Command "try{$r=Invoke-RestMethod -TimeoutSec 8 http://127.0.0.1:1234/v1/models; if(@($r.data.id) -contains '%MODEL_ID%'){exit 0}}catch{}; exit 1"
if errorlevel 1 (
    echo LM Studio is running, but %MODEL_ID% is not available through its API.
    exit /b 1
)

docker compose -f docker-compose.yml ps --status running --services 2>nul | findstr /x "server" >nul
if not errorlevel 1 (
    docker compose -f docker-compose.yml exec -T server python -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://host.docker.internal:1234/v1/models',timeout=8)); assert any(x.get('id')=='%MODEL_ID%' for x in data.get('data',[]))" >nul 2>nul
    if errorlevel 1 (
        echo LM Studio works on Windows, but the OpenMoxie container cannot reach it.
        echo Allow LM Studio on Private networks in Windows Firewall.
        exit /b 1
    )
)

echo LM Studio is ready with %MODEL_ID%.
exit /b 0
