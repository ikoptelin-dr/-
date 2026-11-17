@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0node.exe" (
  echo [XX] Нет node.exe в %~dp0 — скопируйте его из D:\proba
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sluzhebnoe.ps1" start
start "" http://localhost:8081
echo.
echo Браузер открыт: http://localhost:8081 . Это окно можно закрыть.
pause
