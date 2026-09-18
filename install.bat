@echo off
echo Discord Minecraft Bot kuruluyor...
py -m pip install -r requirements.txt
if errorlevel 1 (
    echo Python veya pip bulunamadi.
    pause
    exit /b 1
)
echo.
echo Bot baslatiliyor...
py bot.py
pause
