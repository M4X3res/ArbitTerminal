@echo off
echo ========================================
echo   SMOKE TEST - DEMO MODE (30 seconds)
echo   NO LIVE TRADING - NO REAL ORDERS
echo ========================================
echo.
.venv\Scripts\python.exe smoke_test.py
echo.
pause
