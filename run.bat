@echo off
REM Proxyx — double-click di Windows, langsung jalan.
python -m proxyx %*
if errorlevel 1 (
  echo.
  echo Python belum terpasang? Download di https://www.python.org/downloads/
  echo (centang "Add python.exe to PATH" waktu install)
)
pause
