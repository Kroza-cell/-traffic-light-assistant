@echo off
chcp 65001 >nul
title Claude Multi-Agent Monitor
python "%~dp0traffic_light.py"
pause
