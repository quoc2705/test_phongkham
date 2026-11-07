@echo off
chcp 65001 >nul
echo ========================================================
echo   KHOI DONG HE THONG QUAN LY PHONG KHAM (PHONGKHAM+)
echo ========================================================
echo Truy cap giao dien tai: http://127.0.0.1:8000/login/
echo Nhan Ctrl+C de dung server.
echo.
".venv\Scripts\python.exe" "be\manage.py" runserver 127.0.0.1:8000

