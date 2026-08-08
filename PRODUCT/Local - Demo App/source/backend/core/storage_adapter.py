import logging
import re
from supabase import create_client, Client
from backend.core.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_STORAGE_BUCKET

logger = logging.getLogger(__name__)

def sanitize_folder_name(name: str) -> str:
    if not name: return "Unknown"
    sanitized = re.sub(r'[\\\\/*?:"<>|]', "_", str(name)).strip()
    return sanitized if sanitized else "Unknown"

class StorageAdapter:
    _client: Client = None

    @classmethod
    def get_client(cls) -> Client:
        if not cls._client:
            cls._client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return cls._client

    @staticmethod
    def get_supabase_html_path(model_name: str, team: str, level_1: str, level_2: str, version_name: str) -> str:
        s_model = sanitize_folder_name(model_name)
        s_team = sanitize_folder_name(team)
        s_l1 = sanitize_folder_name(level_1)
        s_l2 = sanitize_folder_name(level_2)
        s_ver = sanitize_folder_name(version_name)

        if version_name.startswith("V00"):
            return f"V00_templates/{s_l1}/{s_l2}/content.html"
        else:
            return f"MP readiness data/{s_model}/{s_team}/{s_l1}/{s_l2}/{s_ver}/content.html"

    @classmethod
    def save_document_html(cls, model_name: str, team: str, level_1: str, level_2: str, version_name: str, html_content: str, background_tasks=None) -> bool:
        """
        Saves document HTML content to Supabase storage.
        """
        try:
            path = cls.get_supabase_html_path(model_name, team, level_1, level_2, version_name)
            client = cls.get_client()
            client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                path=path,
                file=html_content.encode("utf-8"),
                file_options={"upsert": "true", "content-type": "text/html"}
            )
            logger.info(f"[STORAGE SUPABASE] Saved content.html successfully: {path}")
            return True
        except Exception as e:
            logger.error(f"[STORAGE SUPABASE ERROR] Failed to save file: {e}")
            return False

    @classmethod
    def read_document_html(cls, model_name: str, team: str, level_1: str, level_2: str, version_name: str) -> str:
        """
        Reads document HTML content from Supabase storage.
        """
        try:
            path = cls.get_supabase_html_path(model_name, team, level_1, level_2, version_name)
            client = cls.get_client()
            res = client.storage.from_(SUPABASE_STORAGE_BUCKET).download(path)
            return res.decode("utf-8")
        except Exception as e:
            logger.warning(f"[STORAGE SUPABASE] Could not read {model_name}/{version_name}: {e}")
            return ""

    @classmethod
    def sync_database(cls, background_tasks=None):
        """
        Database is now natively on Supabase PostgreSQL. Sync is obsolete.
        """
        pass

    @classmethod
    def create_model_folder(cls, model_name: str, background_tasks=None):
        """
        Supabase creates folders implicitly upon file upload. Nothing to do here.
        """
        pass

    @classmethod
    def delete_model_folder(cls, model_name: str, background_tasks=None):
        """
        Deletes the model folder on Supabase storage.
        """
        if not model_name:
            return
        s_name = sanitize_folder_name(model_name)
        prefix = f"MP readiness data/{s_name}/"
        try:
            client = cls.get_client()
            # List all files with prefix
            files = client.storage.from_(SUPABASE_STORAGE_BUCKET).list(path=prefix)
            if files:
                file_paths = [f"{prefix}{f['name']}" for f in files if f['name'] != '.emptyFolderPlaceholder']
                if file_paths:
                    client.storage.from_(SUPABASE_STORAGE_BUCKET).remove(file_paths)
            logger.info(f"[STORAGE SUPABASE] Deleted model folder: {prefix}")
        except Exception as e:
            logger.error(f"[STORAGE SUPABASE ERROR] Failed to delete model folder: {e}")

    @classmethod
    def reconcile_model_folders(cls, active_model_names: list, background_tasks=None):
        """
        Not needed with direct Supabase Storage usage.
        """
        pass
