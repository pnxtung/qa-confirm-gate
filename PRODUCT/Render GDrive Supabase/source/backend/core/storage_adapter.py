import os
import logging
from backend.core.config import (
    MP_READINESS_DATA_PATH,
    V00_TEMPLATES_PATH,
    STORAGE_DB_PROVIDERS,
    STORAGE_USERDATA_PROVIDERS
)
from backend.core.database import sanitize_folder_name
from backend.core.gdrive_storage import (
    upload_html_content_to_gdrive,
    read_html_content_from_gdrive,
    sync_database_to_gdrive,
    create_folder_on_gdrive,
    delete_folder_on_gdrive,
    reconcile_gdrive_model_folders
)
from backend.core.supabase_storage import (
    upload_html_to_supabase,
    read_html_from_supabase
)
from backend.core.gdrive_queue import gdrive_worker_queue

logger = logging.getLogger(__name__)

class StorageAdapter:
    @staticmethod
    def get_local_html_path(model_name: str, team: str, level_1: str, level_2: str, version_name: str) -> str:
        s_model = sanitize_folder_name(model_name)
        s_team = sanitize_folder_name(team)
        s_l1 = sanitize_folder_name(level_1)
        s_l2 = sanitize_folder_name(level_2)
        s_ver = sanitize_folder_name(version_name)

        if version_name.startswith("V00"):
            return os.path.join(V00_TEMPLATES_PATH, s_l1, s_l2, "content.html")
        else:
            return os.path.join(MP_READINESS_DATA_PATH, s_model, s_team, s_l1, s_l2, s_ver, "content.html")

    @classmethod
    def save_document_html(cls, model_name: str, team: str, level_1: str, level_2: str, version_name: str, html_content: str, background_tasks=None) -> bool:
        # Instant local container cache save
        try:
            local_file_path = cls.get_local_html_path(model_name, team, level_1, level_2, version_name)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with open(local_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            logger.error(f"[STORAGE LOCAL CACHE ERROR] {e}")

        rel_path = f"{model_name}/{team}/{level_1}/{level_2}/{version_name}/content.html"

        # 1. Supabase Storage Provider
        if "SUPABASE" in STORAGE_USERDATA_PROVIDERS:
            gdrive_worker_queue.enqueue(upload_html_to_supabase, rel_path, html_content)

        # 2. Google Drive Storage Provider
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            gdrive_worker_queue.enqueue(upload_html_content_to_gdrive, rel_path, html_content)

        return True

    @classmethod
    def read_document_html(cls, model_name: str, team: str, level_1: str, level_2: str, version_name: str) -> str:
        local_file_path = cls.get_local_html_path(model_name, team, level_1, level_2, version_name)
        if os.path.exists(local_file_path):
            with open(local_file_path, "r", encoding="utf-8") as f:
                return f.read()

        rel_path = f"{model_name}/{team}/{level_1}/{level_2}/{version_name}/content.html"

        # 1. Try reading from Supabase if configured
        if "SUPABASE" in STORAGE_USERDATA_PROVIDERS:
            try:
                content = read_html_from_supabase(rel_path)
                if content:
                    try:
                        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                        with open(local_file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    except:
                        pass
                    return content
            except Exception as e:
                logger.error(f"[STORAGE SUPABASE READ ERROR] {e}")

        # 2. Try reading from Google Drive if configured
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            try:
                content = read_html_content_from_gdrive(rel_path)
                if content:
                    try:
                        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                        with open(local_file_path, "w", encoding="utf-8") as f:
                            f.write(content)
                    except:
                        pass
                    return content
            except Exception as e:
                logger.error(f"[STORAGE GDRIVE READ ERROR] {e}")

        return ""

    @classmethod
    def sync_database(cls, background_tasks=None):
        if "GDRIVE" in STORAGE_DB_PROVIDERS:
            gdrive_worker_queue.enqueue(sync_database_to_gdrive)

    @classmethod
    def create_model_folder(cls, model_name: str, background_tasks=None):
        if not model_name:
            return
        s_name = sanitize_folder_name(model_name)
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            gdrive_worker_queue.enqueue(create_folder_on_gdrive, s_name)

    @classmethod
    def delete_model_folder(cls, model_name: str, background_tasks=None):
        if not model_name:
            return
        s_name = sanitize_folder_name(model_name)
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            gdrive_worker_queue.enqueue(delete_folder_on_gdrive, s_name)

    @classmethod
    def reconcile_model_folders(cls, active_model_names: list, background_tasks=None):
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            gdrive_worker_queue.enqueue(reconcile_gdrive_model_folders, active_model_names)
