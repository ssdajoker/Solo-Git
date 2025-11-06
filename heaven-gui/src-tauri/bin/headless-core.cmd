@echo off
REM Launch the Solo Git headless core via uvicorn.
setlocal
set SCRIPT_DIR=%~dp0
for %%I in ("%SCRIPT_DIR%..\..\..") do set REPO_DIR=%%~fI
cd /d "%REPO_DIR%"
set PORT=%SOLOGIT_HEADLESS_PORT%
if "%PORT%"=="" set PORT=1234
python -m uvicorn sologit.headless_core:app --host 127.0.0.1 --port %PORT% --reload
