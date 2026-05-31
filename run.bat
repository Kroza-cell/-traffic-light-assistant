@echo off
chcp 65001 >nul
title Claude Project Monitor
python "%~dp0monitor.py"
pause
