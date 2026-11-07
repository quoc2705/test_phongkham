@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================================
echo   KHOI DONG UNG DUNG DESKTOP GIA LAP PHONGKHAM+ (TKINTER GUI)
echo ============================================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -X utf8 app_desktop_phongkham.py
) else (
    python -X utf8 app_desktop_phongkham.py
)
pause

