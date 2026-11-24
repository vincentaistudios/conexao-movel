@echo off
setlocal
title Conexao Movel - Configurador Automatico de Permissoes

echo ====================================================================
echo   Conexao Movel - Assistente de Permissoes em 1 Clique (Windows)
echo ====================================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto_setup_phone_permissions.ps1"

echo.
pause

