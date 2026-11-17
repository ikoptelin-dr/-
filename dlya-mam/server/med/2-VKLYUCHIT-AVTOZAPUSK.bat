@echo off
chcp 65001 >nul
net session >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
cd /d "%~dp0"
schtasks /Create /TN "med - sajt" /TR "\"%~dp0ZAPUSTIT-SAJT.bat\"" /SC ONSTART /DELAY 0001:00 /RU SYSTEM /RL HIGHEST /F >nul
if errorlevel 1 (
  echo [XX] Не удалось создать задачу «med - sajt»
) else (
  echo [OK] Задача «med - sajt» создана: сайт запускается при включении компьютера
)
if exist "%~dp0OBSHCHIJ-CADDY.txt" (
  echo [OK] Режим «общий Caddy»: свой Caddy не запускается, добавьте блоки из OBSHCHIJ-CADDY.txt в Caddyfile друга
) else (
  echo [XX] Нет файла OBSHCHIJ-CADDY.txt — без него сайт не будет доступен по домену
)
call "%~dp0ZAPUSTIT-SAJT.bat"
pause
