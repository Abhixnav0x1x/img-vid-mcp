@echo off
REM ============================================================
REM  imagemcp one-command setup (Windows)
REM  Usage: setup.cmd [--no-wire]
REM    --no-wire   skip OpenCode wiring (deps + .env + verify only)
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title imagemcp setup

set "WIRE=1"
if /i "%~1"=="--no-wire" set "WIRE=0"

echo.
echo  ===== imagemcp setup =====
echo.

REM ---------- 1. Python ----------
echo [1/6] Checking Python...
set "PY=python"
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo        'python' not found, trying 'py -3'...
  set "PY=py -3"
  %PY% --version >nul 2>&1
  if errorlevel 1 (
    echo [FAIL] Python 3.10+ is required: https://www.python.org/downloads/
    echo        Re-run this script after installing ^(tick "Add to PATH"^).
    pause
    exit /b 1
  )
)
for /f "tokens=*" %%v in ('%PY% --version 2^>^&1') do echo        %%v

REM ---------- 2. ffmpeg (optional but recommended) ----------
echo [2/6] Checking ffmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo        [WARN] ffmpeg not found - video pages with split streams need it.
  echo               Install: choco install ffmpeg  ^(or https://ffmpeg.org/download.html^)
) else (
  echo        ffmpeg OK
)

REM ---------- 3. Dependencies ----------
echo [3/6] Installing Python dependencies ^(may take a few minutes^)...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo [FAIL] pip install failed - check your network and re-run.
  pause
  exit /b 1
)

REM ---------- 4. .env ----------
echo [4/6] Configuring .env...
if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  echo        created .env from .env.example
) else (
  echo        .env already exists - kept as-is
)

REM ---------- 5. Verify ----------
echo [5/6] Verifying server...
%PY% -c "import server,json; s=server.status(); print('       version:',s['version'],'| ddgs:',s['ddgs_available'],'| imgopt:',s['imgopt_available'],'| ytdlp:',s['ytdlp_available'])"
if errorlevel 1 (
  echo [FAIL] server failed to start - see error above.
  pause
  exit /b 1
)

REM ---------- 6. Wire into OpenCode (global, backup first) ----------
if "%WIRE%"=="0" (
  echo [6/6] Skipped OpenCode wiring ^(--no-wire^).
  goto done
)
echo [6/6] Wiring into OpenCode global config...
%PY% -c "import json,os,shutil; p=os.path.join(os.path.expanduser('~'),'.config','opencode','opencode.json'); os.makedirs(os.path.dirname(p),exist_ok=True); cfg=json.load(open(p,encoding='utf-8')) if os.path.exists(p) else {}; shutil.copy(p,p+'.bak') if os.path.exists(p) else None; cfg['$schema']=cfg.get('$schema','https://opencode.ai/config.json'); m=cfg.setdefault('mcp',{}); m['imagemcp']={'type':'local','command':['python',os.path.join(os.getcwd(),'server.py')],'cwd':os.getcwd(),'enabled':True,'timeout':30000,'environment':{'MEDIA_ROOT':'./public/assets','STORAGE_DIR':'./.storage','IMAGEOPTIMISER_PATH':'../imageoptimiser','IMGOPT_ENABLED':'1','IMGOPT_QUALITY':'80','ENABLE_CAMOUFOX':'0','MAX_FILES':'100'}}; json.dump(cfg,open(p,'w',encoding='utf-8'),indent=2); print('       wired global config:',p,' (backup: opencode.json.bak)')"
if errorlevel 1 (
  echo [WARN] auto-wire failed - wire manually, see README "Hooking up an agent".
  goto done
)

where opencode >nul 2>&1
if errorlevel 1 (
  echo        opencode CLI not on PATH - restart your terminal, then run: opencode mcp list
) else (
  echo.
  echo        --- opencode mcp list ---
  call opencode mcp list
)

:done
echo.
echo  ===== setup complete =====
echo  Restart OpenCode if it is running, then ask an agent:
echo    use the imagemcp tools to search for "hero coffee shop" images and download the best one into hero/
echo.
pause
