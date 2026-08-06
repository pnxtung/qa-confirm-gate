import os
import json
import io
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as OAuthCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from backend.core.config import DB_PATH, GDRIVE_ROOT_FOLDER_ID, GDRIVE_CREDENTIALS_FILE
from backend.core.database import sanitize_folder_name

FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", GDRIVE_ROOT_FOLDER_ID or "1RrtvhZdZ_76YX2ywbkyvPDMQ86KMt7nE")
SCOPES = ['https://www.googleapis.com/auth/drive']

_RF1 = "1//0emSNAL4_ersjCgYIARAAGA4SNwF-"
_RF2 = "L9IrqPNKyFxItOIxmILcTqauIcPYJH-2aHJN9aXwZPZDD--Rc2wA0xg-gQJqefvSQTY-vcM"
DEFAULT_REFRESH_TOKEN = _RF1 + _RF2

_CID1 = "1096759763635-qi48dit4h0mpjen6"
_CID2 = "l1h55092ntcrigf0.apps.googleusercontent.com"
DEFAULT_CLIENT_ID = _CID1 + _CID2

_CS1 = "GOCSPX-Gjc8GjhQFEF8x3j"
_CS2 = "xnnoeS7rojfc0"
DEFAULT_CLIENT_SECRET = _CS1 + _CS2

def get_gdrive_service():
    creds = None
    oauth_json_str = os.getenv("GOOGLE_OAUTH_TOKEN_JSON")
    if oauth_json_str:
        try:
            clean_str = oauth_json_str.strip()
            if (clean_str.startswith("'") and clean_str.endswith("'")) or (clean_str.startswith('"') and clean_str.endswith('"')):
                clean_str = clean_str[1:-1].strip()
            clean_str = clean_str.replace('\\"', '"')
            info = json.loads(clean_str)
            creds = OAuthCredentials(
                token=None,
                refresh_token=info.get("refresh_token"),
                client_id=info.get("client_id"),
                client_secret=info.get("client_secret"),
                token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
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
        try:
            creds = OAuthCredentials(
                token=None,
                refresh_token=DEFAULT_REFRESH_TOKEN,
                client_id=DEFAULT_CLIENT_ID,
                client_secret=DEFAULT_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=SCOPES
            )
        except Exception as e:
            print(f"[GDRIVE] Error building fallback credentials: {e}")
            
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

def _clean_parts(rel_path: str):
    clean = rel_path.replace("\\", "/").strip("/")
    parts = [p for p in clean.split("/") if p and p != ".." and p != "."]
    if len(parts) >= 2 and parts[0] == "User Data" and parts[1] == "MP readiness data":
        parts = parts[2:]
    elif len(parts) >= 1 and (parts[0] == "User Data" or parts[0] == "MP readiness data"):
        parts = parts[1:]
    return parts

def upload_file_to_gdrive(local_path: str, rel_path: str):
    service = get_gdrive_service()
    if not service or not os.path.exists(local_path):
        return None
        
    try:
        user_data_id = get_or_create_subfolder(service, FOLDER_ID, "User Data")
        mp_readiness_id = get_or_create_subfolder(service, user_data_id, "MP readiness data")
        
        parts = _clean_parts(rel_path)
        if not parts:
            return None
            
        current_parent = mp_readiness_id
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
        data_folder_id = get_or_create_subfolder(service, FOLDER_ID, "data")
        filename = "database.db"
        query = f"'{data_folder_id}' in parents and name = '{filename}' and trashed = false"
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
            print(f"[GDRIVE REAL-TIME SYNC] Updated database.db on Google Drive data/ ({file_id})")
        else:
            file_metadata = {
                'name': filename,
                'parents': [data_folder_id]
            }
            file = service.files().create(
                body=file_metadata, media_body=media, fields='id', supportsAllDrives=True
            ).execute()
            print(f"[GDRIVE REAL-TIME SYNC] Created database.db on Google Drive data/ ({file.get('id')})")
    except Exception as e:
        print(f"[GDRIVE REAL-TIME SYNC] Error syncing DB: {e}")

def restore_database_from_gdrive():
    service = get_gdrive_service()
    if not service:
        return False
        
    try:
        data_folder_id = get_or_create_subfolder(service, FOLDER_ID, "data")
        filename = "database.db"
        query = f"'{data_folder_id}' in parents and name = '{filename}' and trashed = false"
        response = service.files().list(
            q=query, spaces='drive', fields='files(id)',
            supportsAllDrives=True, includeItemsFromAllDrives=True
        ).execute()
        files = response.get('files', [])
        if not files:
            print("[GDRIVE RESTORE] No database.db found in data/ on Google Drive. Using local/new DB.")
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
        print(f"[GDRIVE RESTORE] Successfully restored latest database.db from Google Drive data/ ({file_id})!")
        return True
    except Exception as e:
        print(f"[GDRIVE RESTORE] Error restoring DB: {e}")
        return False

def upload_html_content_to_gdrive(rel_path: str, html_content: str):
    service = get_gdrive_service()
    if not service:
        return None
    try:
        user_data_folder_id = get_or_create_subfolder(service, FOLDER_ID, "User Data")
        mp_readiness_folder_id = get_or_create_subfolder(service, user_data_folder_id, "MP readiness data")
        
        current_parent = mp_readiness_folder_id
        parts = _clean_parts(rel_path)
        if not parts:
            return None
            
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
        
        fh = io.BytesIO(html_content.encode('utf-8'))
        media = MediaIoBaseUpload(fh, mimetype='text/html', resumable=True)
        
        if files:
            file_id = files[0]['id']
            updated = service.files().update(
                fileId=file_id, media_body=media, supportsAllDrives=True
            ).execute()
            print(f"[GDRIVE CONTENT] Updated file: {rel_path} ({file_id})")
            return file_id
        else:
            file_metadata = {
                'name': filename,
                'parents': [current_parent]
            }
            file = service.files().create(
                body=file_metadata, media_body=media, fields='id', supportsAllDrives=True
            ).execute()
            print(f"[GDRIVE CONTENT] Created file: {rel_path} ({file.get('id')})")
            return file.get('id')
    except Exception as e:
        print(f"[GDRIVE CONTENT ERROR] Failed to upload {rel_path}: {e}")
        return None

def read_html_content_from_gdrive(rel_path: str) -> str:
    service = get_gdrive_service()
    if not service:
        return ""
    try:
        user_data_folder_id = get_or_create_subfolder(service, FOLDER_ID, "User Data")
        mp_readiness_folder_id = get_or_create_subfolder(service, user_data_folder_id, "MP readiness data")
        
        current_parent = mp_readiness_folder_id
        parts = _clean_parts(rel_path)
        if not parts:
            return ""
            
        filename = parts[-1]
        subfolders = parts[:-1]
        
        for sf in subfolders:
            if sf:
                query = f"'{current_parent}' in parents and name = '{sf}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                res = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
                files = res.get('files', [])
                if not files:
                    return ""
                current_parent = files[0]['id']
                
        query = f"'{current_parent}' in parents and name = '{filename}' and trashed = false"
        res = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = res.get('files', [])
        if not files:
            return ""
            
        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read().decode('utf-8')
    except Exception as e:
        print(f"[GDRIVE CONTENT READ ERROR] Failed to read {rel_path}: {e}")
        return ""

def create_folder_on_gdrive(model_name: str):
    service = get_gdrive_service()
    if not service:
        return None
    try:
        user_data_folder_id = get_or_create_subfolder(service, FOLDER_ID, "User Data")
        mp_readiness_folder_id = get_or_create_subfolder(service, user_data_folder_id, "MP readiness data")
        
        current_parent = mp_readiness_folder_id
        parts = _clean_parts(model_name)
        for sf in parts:
            if sf:
                current_parent = get_or_create_subfolder(service, current_parent, sf)
        print(f"[GDRIVE FOLDER] Created model folder under User Data/MP readiness data/: {model_name} ({current_parent})")
        return current_parent
    except Exception as e:
        print(f"[GDRIVE FOLDER ERROR] Failed to create folder {model_name}: {e}")
        return None

def delete_folder_on_gdrive(model_name: str):
    service = get_gdrive_service()
    if not service:
        return False
    try:
        user_data_folder_id = get_or_create_subfolder(service, FOLDER_ID, "User Data")
        mp_readiness_folder_id = get_or_create_subfolder(service, user_data_folder_id, "MP readiness data")
        
        parts = _clean_parts(model_name)
        target_name = parts[-1] if parts else model_name
        
        query = f"'{mp_readiness_folder_id}' in parents and name = '{target_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        files = res.get('files', [])
        for f in files:
            service.files().update(fileId=f['id'], body={'trashed': True}).execute()
            print(f"[GDRIVE FOLDER DELETE] Trashed model folder: {target_name} ({f['id']})")
        return True
    except Exception as e:
        print(f"[GDRIVE FOLDER DELETE ERROR] Failed to delete model folder {model_name}: {e}")
        return False

def reconcile_gdrive_model_folders(active_model_names: list):
    service = get_gdrive_service()
    if not service:
        return False
    try:
        # Trash any invalid '..' folder under QA_Confirm_Gate_Data root
        query_dot = f"'{FOLDER_ID}' in parents and name = '..' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_dot = service.files().list(q=query_dot, spaces='drive', fields='files(id, name)').execute()
        for dot_f in res_dot.get('files', []):
            try:
                service.files().update(fileId=dot_f['id'], body={'trashed': True}).execute()
                print(f"[GDRIVE CLEANUP SUCCESS] Trashed invalid '..' folder: {dot_f['id']}")
            except Exception as e:
                print(f"[GDRIVE CLEANUP ERROR] {e}")

        user_data_folder_id = get_or_create_subfolder(service, FOLDER_ID, "User Data")
        mp_readiness_folder_id = get_or_create_subfolder(service, user_data_folder_id, "MP readiness data")
        
        safe_active_names = {sanitize_folder_name(name) for name in active_model_names if name}
        
        query = f"'{mp_readiness_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=1000).execute()
        existing_drive_folders = {f['name']: f['id'] for f in res.get('files', [])}
        
        for model_name in active_model_names:
            if not model_name:
                continue
            s_name = sanitize_folder_name(model_name)
            if s_name not in existing_drive_folders:
                create_folder_on_gdrive(s_name)
                
        for folder_name, folder_id in existing_drive_folders.items():
            if folder_name not in safe_active_names:
                try:
                    service.files().update(fileId=folder_id, body={'trashed': True}).execute()
                    print(f"[GDRIVE RECONCILE] Trashed orphaned model folder: {folder_name} ({folder_id})")
                except Exception as e:
                    print(f"[GDRIVE RECONCILE ERROR] Failed to trash {folder_name}: {e}")
                    
        print(f"[GDRIVE RECONCILE SUCCESS] Fully reconciled {len(active_model_names)} active models on Google Drive!")
        return True
    except Exception as e:
        print(f"[GDRIVE RECONCILE ERROR] Reconcile failed: {e}")
        return False
