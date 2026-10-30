@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo Chua cai dat. Hay chay setup.bat truoc.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
python main.py %*
pause
