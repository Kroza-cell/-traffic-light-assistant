@echo off
chcp 65001 >nul
title Claude 状态红绿灯
python "%~dp0traffic_light.py"
pause
