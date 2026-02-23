@echo off
REM =============================================================================
REM Student Admission Form OCR System - Windows Batch Wrapper
REM =============================================================================
REM This is a simple wrapper that calls the PowerShell script
REM =============================================================================

powershell.exe -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
