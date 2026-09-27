@echo off
title Metrolab NAWI Platform
cd /d "%~dp0"

echo ===================================================================
echo     METROLAB: OIML R-76 Digital Testing & Verification Platform
echo ===================================================================
echo.
echo Launching Metrolab Unified Web & API Server on http://localhost:8000 ...
echo.
echo Opening browser at: http://localhost:8000/
start http://localhost:8000/
echo.
python server.py
pause
