@echo off
REM Rebuild the Cooperative Development Award Panel on Windows.
REM Easiest use: put the USAspending zips (Prime....zip) in this folder and double-click this file.
REM If there are none here, it uses every Prime*.zip in your Downloads folder.
REM After verification: run_all.bat --final
setlocal enabledelayedexpansion
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" on the first installer screen. Then run this again.
  goto :end
)
echo Checking Python packages...
python -m pip install --quiet pandas matplotlib pytest

set FINAL=
if /I "%~1"=="--final" set FINAL=--final
set FOUND=
cd code
REM USAspending zips: any Prime*.zip in this folder; if none, any in your Downloads folder
for %%F in ("%~dp0Prime*.zip") do (
  set FOUND=1
  echo Using USAspending file: %%~nxF
  python 01_ingest.py "%%~fF" || goto :err
)
if not defined FOUND for %%F in ("%USERPROFILE%\Downloads\Prime*.zip") do (
  set FOUND=1
  echo Using USAspending file: %%~nxF
  python 01_ingest.py "%%~fF" || goto :err
)
if not defined FOUND echo No USAspending zip found - rebuilding from the files already in data\raw\usaspending
python 02_build.py || goto :err
python 03_qa.py || goto :err
python 04_figures.py %FINAL% || goto :err
python 05_document.py %FINAL% || goto :err
echo.
echo ============================================================
echo Done. Compare data\processed\qa_report.txt with
echo docs\qa_report_REFERENCE.txt  (they should show the same numbers)
echo ============================================================
goto :end
:err
echo.
echo A step failed - copy the error above into the chat.
:end
echo.
pause
