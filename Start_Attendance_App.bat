@echo off
title Attendance Master Launcher
color 0b
echo =======================================================
echo          ATTENDANCE MASTER - POINTAGE RH AUTOMATOR
echo =======================================================
echo.

set PYTHON_PATH="C:\Users\Dell\anaconda3\python.exe"

if exist %PYTHON_PATH% (
    echo [OK] Using Anaconda Python at: %PYTHON_PATH%
    set PY_EXE=%PYTHON_PATH%
) else (
    echo [INFO] Looking for Python in system PATH...
    set PY_EXE=python
)

echo.
echo Starting web server on http://localhost:5000 ...
echo Opening your web browser in 2 seconds...

start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

%PY_EXE% app.py

pause
