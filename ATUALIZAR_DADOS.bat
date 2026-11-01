@echo off
chcp 65001 >nul
title Baixar dados do SINAN
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo  O dashboard ainda nao foi instalado. Rode primeiro o INSTALAR.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" baixar_dados.py %*
pause
