import os
import urllib.request
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(SOURCE_DIR)

TOOLS_DIR = os.path.join(ROOT_DIR, "tools")
os.makedirs(TOOLS_DIR, exist_ok=True)

CLOUDFLARED_EXE = os.path.join(TOOLS_DIR, "cloudflared.exe")
DOWNLOAD_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

print("==================================================")
print("SETTING UP CLOUDFLARE TUNNEL FOR INTERNET ACCESS")
print("==================================================")

if not os.path.exists(CLOUDFLARED_EXE):
    print("Downloading official cloudflared.exe from Cloudflare...")
    try:
        urllib.request.urlretrieve(DOWNLOAD_URL, CLOUDFLARED_EXE)
        print("SUCCESS: Downloaded cloudflared.exe!")
    except Exception as e:
        print(f"Error downloading cloudflared.exe: {e}")
        sys.exit(1)
else:
    print("cloudflared.exe is already present.")

# Create Start_Internet_Tunnel.bat at root
BAT_CONTENT = """@echo off
title QA Confirm Gate - Internet Public Tunnel
echo ==================================================
echo STARTING INTERNET TUNNEL VIA CLOUDFLARE
echo Make sure Start_Server.bat is running on http://localhost:8000!
echo ==================================================
echo.
"%~dp0tools\\cloudflared.exe" tunnel --url http://localhost:8000
pause
"""

BAT_PATH = os.path.join(ROOT_DIR, "Start_Internet_Tunnel.bat")
with open(BAT_PATH, "w", encoding="utf-8") as f:
    f.write(BAT_CONTENT)

print(f"SUCCESS: Created '{BAT_PATH}'!")
print("==================================================")
