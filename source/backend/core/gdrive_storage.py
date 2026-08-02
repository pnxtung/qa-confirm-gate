import os
import json
import io
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from backend.core.config import DB_PATH

FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "1RrtvhZdZ_76YX2ywbkyvPDMQ86KMt7nE")
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_gdrive_service():
    creds = None
    
    # 1. Thử dùng OAuth 2.0 Credentials (Đóng vai trực tiếp chính tài khoản Gmail 15GB của Sếp)
    oauth_json_str = os.getenv("GOOGLE_OAUTH_TOKEN_JSON")
    if oauth_json_str:
        try:
            info = json.loads(oauth_json_str)
            creds = OAuthCredentials(
                token=None,
                refresh_token=info.get("refresh_token"),
                client_id=info.get("client_id"),
                client_secret=info.get("client_secret"),
                token_uri="https://oauth2.googleapis.com/token",
                scopes=SCOPES
            )
        except Exception as e:
            print(f"[GDRIVE] Error parsing GOOGLE_OAUTH_TOKEN_JSON: {e}")
            
    if not creds:
        local_oauth = os.path.join(os.path.dirname(__file__), "gdrive_oauth_token.json")
        if os.path.exists(local_oauth):
            try:
                with open(local_oauth, "r", encoding="utf-8") as f:
                    info = json.load(f)
                creds = OAuthCredentials(
                    token=None,
                    refresh_token=info.get("refresh_token"),
                    client_id=info.get("client_id"),
                    client_secret=info.get("client_secret"),
                    token_uri="https://oauth2.googleapis.com/token",
                    scopes=SCOPES
                )
            except Exception as e:
                print(f"[GDRIVE] Error reading gdrive_oauth_token.json: {e}")
                
    # 2. Dùng Service Account Credentials
    if not creds:
        creds_json_str = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json_str:
            try:
                info = json.loads(creds_json_str)
                creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            except Exception as e:
                print(f"[GDRIVE] Error parsing GOOGLE_CREDENTIALS_JSON: {e}")
                
    if not creds:
        local_creds = os.path.join(os.path.dirname(__file__), "credentials.json")
        if os.path.exists(local_creds):
            creds = service_account.Credentials.from_service_account_file(local_creds, scopes=SCOPES)
            
    if not creds:
        return None
        
    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"[GDRIVE] Error building drive service: {e}")
        return None

def get_or_create_subfolder(service, parent_id, folder_name):
    query = f"'{parent_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    response = service.files().list(
        q=query, spaces='drive', fields='files(id, name)',
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    files = response.get('files', [])
    if files:
        return files[0]['id']
    
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(
        body=file_metadata, fields='id', supportsAllDrives=True
    ).execute()
    return folder.get('id')

def upload_file_to_gdrive(local_path: str, rel_path: str):
    service = get_gdrive_service()
    if not service or not os.path.exists(local_path):
        return None
        
    try:
        current_parent = FOLDER_ID
        parts = rel_path.replace("\\", "/").strip("/").split("/")
        filename = parts[-1]
        subfolders = parts[:-1]
        
        for sf in subfolders:
            if sf:
                current_parent = get_or_create_subfolder(service, current_parent, sf)
                
        query = f"'{current_parent}' in parents and name = '{filename}' and trashed = false"
        response = service.files().list(
            q=query, spaces='drive', fields='files(id)',
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        files = response.get('files', [])
        
        media = MediaFileUpload(local_path, resumable=True)
        if files:
            file_id = files[0]['id']
            updated = service.files().update(
                fileId=file_id, media_body=media, supportsAllDrives=True
            ).execute()
            print(f"[GDRIVE] Updated file: {filename} ({file_id})")
            return file_id
        else:
            file_metadata = {
                'name': filename,
                'parents': [current_parent]
            }
            file = service.files().create(
                body=file_metadata, media_body=media, fields='id', supportsAllDrives=True
            ).execute()
            print(f"[GDRIVE] Created file: {filename} ({file.get('id')})")
            return file.get('id')
    except Exception as e:
        print(f"[GDRIVE] Error uploading {local_path}: {e}")
        return None

def sync_database_to_gdrive():
    if not os.path.exists(DB_PATH):
        return
    service = get_gdrive_service()
    if not service:
        return
        
    try:
        filename = "database.db"
        query = f"'{FOLDER_ID}' in parents and name = '{filename}' and trashed = false"
        response = service.files().list(
            q=query, spaces='drive', fields='files(id)',
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        files = response.get('files', [])
        
        media = MediaFileUpload(DB_PATH, mimetype='application/x-sqlite3', resumable=True)
        if files:
            file_id = files[0]['id']
            service.files().update(
                fileId=file_id, media_body=media, supportsAllDrives=True
            ).execute()
            print(f"[GDRIVE REAL-TIME SYNC] Updated database.db on Google Drive ({file_id})")
        else:
            file_metadata = {
                'name': filename,
                'parents': [FOLDER_ID]
            }
            file = service.files().create(
                body=file_metadata, media_body=media, fields='id', supportsAllDrives=True
            ).execute()
            print(f"[GDRIVE REAL-TIME SYNC] Created database.db on Google Drive ({file.get('id')})")
    except Exception as e:
        print(f"[GDRIVE REAL-TIME SYNC] Error syncing DB: {e}")

def restore_database_from_gdrive():
    service = get_gdrive_service()
    if not service:
        return False
        
    try:
        filename = "database.db"
        query = f"'{FOLDER_ID}' in parents and name = '{filename}' and trashed = false"
        response = service.files().list(
            q=query, spaces='drive', fields='files(id)',
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        files = response.get('files', [])
        if not files:
            print("[GDRIVE RESTORE] No database.db found on Google Drive. Using local/new DB.")
            return False
            
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            
        fh = io.FileIO(DB_PATH, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.close()
        print(f"[GDRIVE RESTORE] Successfully restored latest database.db from Google Drive ({file_id})!")
        return True
    except Exception as e:
        print(f"[GDRIVE RESTORE] Error restoring DB: {e}")
        return False
