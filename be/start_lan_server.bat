@echo off
setlocal

REM Chay server cho client trong LAN truy cap.
REM Su dung: start_lan_server.bat 192.168.1.10 8000

set HOST=%1
if "%HOST%"=="" set HOST=0.0.0.0

set PORT=%2
if "%PORT%"=="" set PORT=8000

echo [1/2] Thu thap static files...
python manage.py collectstatic --noinput
if errorlevel 1 (
  echo Collectstatic that bai.
  exit /b 1
)

echo [2/2] Khoi dong ASGI server tai %HOST%:%PORT% ...
daphne -b %HOST% -p %PORT% phongkham.asgi:application
