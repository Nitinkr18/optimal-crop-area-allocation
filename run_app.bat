@echo off
REM Launch the CropLP web app (opens http://127.0.0.1:8000 in your browser)
cd /d "%~dp0"
python webapp\server.py
pause
