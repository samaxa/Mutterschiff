@echo off
REM Legt die gemeinsame Python-Umgebung .venv im Repository an
REM und installiert alle Pakete aus requirements.txt.
REM Auf PC und Laptop einfach doppelklicken (oder im Terminal ausfuehren).

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Erstelle .venv ...
    py -3.12 -m venv .venv || python -m venv .venv
)

echo Installiere Pakete ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Fertig. Interpreter fuer PyCharm: %CD%\.venv\Scripts\python.exe
pause
