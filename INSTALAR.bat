@echo off
chcp 65001 >nul
title Instalar Dashboard SINAN
cd /d "%~dp0"
echo.
echo  === Instalando o Dashboard SINAN (precisa de internet so desta vez) ===
echo.
where uv >nul 2>nul
if errorlevel 1 (
  echo  Instalando o gerenciador uv...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
rem o instalador do uv coloca o programa em %USERPROFILE%\.local\bin
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
  echo.
  echo  ERRO: nao foi possivel instalar o uv. Verifique a internet e tente de novo.
  pause
  exit /b 1
)
uv sync --no-dev
if errorlevel 1 (
  echo.
  echo  ERRO na instalacao. Verifique a internet e tente de novo.
  pause
  exit /b 1
)
echo.
echo  Pronto! Agora use ABRIR_DASHBOARD.bat
echo  ^(na primeira vez, va em "Baixar dados" dentro do dashboard^)
echo.
pause
