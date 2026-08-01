import os
import sys
import shutil
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(SOURCE_DIR)
ENV_DIR = os.path.join(ROOT_DIR, "python_env")

print(f"Building Ultra-Lean Portable Python at: {ENV_DIR}")

if os.path.exists(ENV_DIR):
    shutil.rmtree(ENV_DIR, ignore_errors=True)

sys_python_dir = os.path.dirname(sys.executable)

EXCLUDE_SYS_FOLDERS = {"Doc", "tcl", "Tools", "include", "libs"}
EXCLUDE_LIB_FOLDERS = {"test", "idlelib", "turtledemo", "ensurepip"}

print("Copying essential Python runtime files...")
for item in os.listdir(sys_python_dir):
    if item in EXCLUDE_SYS_FOLDERS or item in [".git", "__pycache__"]:
        continue
    s = os.path.join(sys_python_dir, item)
    d = os.path.join(ENV_DIR, item)
    if os.path.isdir(s):
        shutil.copytree(s, d, dirs_exist_ok=True)
    else:
        shutil.copy2(s, d)

lib_dir = os.path.join(ENV_DIR, "Lib")
for folder in EXCLUDE_LIB_FOLDERS:
    target = os.path.join(lib_dir, folder)
    if os.path.exists(target):
        shutil.rmtree(target, ignore_errors=True)

scripts_dir = os.path.join(ENV_DIR, "Scripts")
os.makedirs(scripts_dir, exist_ok=True)
for exe in ["python.exe", "pythonw.exe", "python311.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll"]:
    src = os.path.join(ENV_DIR, exe)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(scripts_dir, exe))

PYTHON_EXE = os.path.join(ENV_DIR, "python.exe")
REQUIREMENTS_TXT = os.path.join(SOURCE_DIR, "requirements.txt")

print("Installing dependencies from requirements.txt...")
subprocess.run([PYTHON_EXE, "-m", "pip", "install", "--no-cache-dir", "-r", REQUIREMENTS_TXT], check=True)

print("Installing pystray & Pillow for system tray UI...")
subprocess.run([PYTHON_EXE, "-m", "pip", "install", "--no-cache-dir", "pystray", "Pillow"], check=True)

print("Verifying installed packages in ultra-lean portable Python...")
test_cmd = [PYTHON_EXE, "-c", "import fastapi, uvicorn, jinja2, dotenv, pystray, PIL; print('ULTRA LEAN PORTABLE PYTHON ALL IMPORTS OK!')"]
res = subprocess.run(test_cmd, capture_output=True, text=True, cwd=SOURCE_DIR)
print(res.stdout)
if res.returncode == 0:
    print("SUCCESS: Ultra-lean Standalone Portable Python is built and ready!")
else:
    print("ERROR:", res.stderr)
    sys.exit(1)
