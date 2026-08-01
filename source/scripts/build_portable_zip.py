import os
import sys
import zipfile
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.dirname(SCRIPT_DIR)
ROOT_DIR = os.path.dirname(SOURCE_DIR)

ZIP_OUTPUT_PATH = os.path.join(ROOT_DIR, "QA_Confirm_Gate_Portable.zip")

EXCLUDE_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".idea", ".vscode", "build"
}

EXCLUDE_FILES = {
    ".DS_Store", "Thumbs.db", "vbs_cmd_str.log", "vbs_debug.txt", "vbs_test.log",
    "server.log", "server_err.log", "launch_cmd.log", "launch_debug.log"
}

EXCLUDE_EXTENSIONS = {
    ".pyc", ".pyo", ".log", ".tmp", ".spec"
}

print("==================================================")
print("CREATING PORTABLE ZIP PACKAGE FOR COLLEAGUES...")
print(f"Target Zip File: {ZIP_OUTPUT_PATH}")
print("==================================================")

start_time = time.time()

if os.path.exists(ZIP_OUTPUT_PATH):
    os.remove(ZIP_OUTPUT_PATH)

total_files_added = 0

with zipfile.ZipFile(ZIP_OUTPUT_PATH, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
    # Add root Start_Server.bat if present
    start_bat_path = os.path.join(ROOT_DIR, "Start_Server.bat")
    if os.path.exists(start_bat_path):
        zipf.write(start_bat_path, "Start_Server.bat")
        total_files_added += 1

    folders_to_include = ["python_env", "User Data", "source"]
    
    for folder in folders_to_include:
        folder_path = os.path.join(ROOT_DIR, folder)
        if not os.path.exists(folder_path):
            print(f"WARNING: Folder {folder_path} not found! Skipping...")
            continue
            
        print(f"Packaging folder: {folder}...")
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if file in EXCLUDE_FILES:
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDE_EXTENSIONS:
                    continue
                    
                abs_filepath = os.path.join(root, file)
                rel_filepath = os.path.relpath(abs_filepath, ROOT_DIR)
                
                zipf.write(abs_filepath, rel_filepath)
                total_files_added += 1

elapsed = time.time() - start_time
size_mb = os.path.getsize(ZIP_OUTPUT_PATH) / (1024 * 1024)

print("--------------------------------------------------")
print(f"SUCCESS: Built '{os.path.basename(ZIP_OUTPUT_PATH)}'")
print(f"Total Files Packed: {total_files_added}")
print(f"Archive Size: {size_mb:.2f} MB")
print(f"Time Taken: {elapsed:.1f} seconds")
print(f"Output Location: {ZIP_OUTPUT_PATH}")
print("==================================================")
