@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo [LOI] Chua cai Python. Tai Python 3.10+ tai https://www.python.org/downloads/
    echo       Nho tick "Add python.exe to PATH" khi cai dat.
    pause
    exit /b 1
)
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Cai dat xong. Chay run.bat de khoi dong.
pause
