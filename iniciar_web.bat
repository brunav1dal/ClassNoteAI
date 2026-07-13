@echo off
cd /d "%~dp0"
start "ClassNote AI Web" /B python -u src\web_api.py
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8000
