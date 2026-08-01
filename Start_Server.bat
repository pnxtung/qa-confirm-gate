@echo off
title QA Confirm Gate Server
cd /d "%~dp0source"

if exist "%~dp0python_env\python.exe" (
    "%~dp0python_env\python.exe" -m uvicorn main:app --reload
) else if exist "%~dp0python_env\Scripts\python.exe" (
    "%~dp0python_env\Scripts\python.exe" -m uvicorn main:app --reload
) else (
    python -m uvicorn main:app --reload
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==================================================
    echo Error starting QA Confirm Gate Server!
    echo ==================================================
    pause
)
