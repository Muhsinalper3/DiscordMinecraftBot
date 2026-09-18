@echo off
echo EXE olusturuluyor...
py -m pip install -r requirements.txt
py -m pip install pyinstaller
py -m PyInstaller --onefile --windowed --name DiscordMinecraftBot bot.py
echo.
echo EXE: dist\DiscordMinecraftBot.exe
pause
