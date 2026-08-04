@echo off
title QA Confirm Gate - Cloudflare Public Tunnel
echo ==================================================
echo STARTING INTERNET TUNNEL VIA CLOUDFLARE
echo Make sure Start_Server.bat is running on http://localhost:8000!
echo ==================================================
echo.
"%~dp0tools\cloudflared.exe" tunnel --url http://localhost:8000
pause
