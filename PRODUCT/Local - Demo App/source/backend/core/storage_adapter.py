import os
import shutil
import logging
from backend.core.config import (
    MP_READINESS_DATA_PATH,
    V00_TEMPLATES_PATH
)
from backend.core.database import sanitize_folder_name

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
        """
        Saves document HTML content to local disk storage.
        """
        try:
            local_file_path = cls.get_local_html_path(model_name, team, level_1, level_2, version_name)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with open(local_file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"[STORAGE LOCAL] Saved content.html successfully: {local_file_path}")
            return True
        except Exception as e:
            logger.error(f"[STORAGE LOCAL ERROR] Failed to save local file: {e}")
            return False

    @classmethod
    def read_document_html(cls, model_name: str, team: str, level_1: str, level_2: str, version_name: str) -> str:
        """
        Reads document HTML content from local disk storage.
        """
        local_file_path = cls.get_local_html_path(model_name, team, level_1, level_2, version_name)
        if os.path.exists(local_file_path):
            with open(local_file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @classmethod
    def sync_database(cls, background_tasks=None):
        """
        Local database sync stub (Database is saved directly to DB_PATH).
        """
        pass

    @classmethod
    def create_model_folder(cls, model_name: str, background_tasks=None):
        """
        Creates the model root folder on local disk storage.
        """
        if not model_name:
            return
        s_name = sanitize_folder_name(model_name)
        try:
            target_dir = os.path.join(MP_READINESS_DATA_PATH, s_name).replace("\\", "/")
            os.makedirs(target_dir, exist_ok=True)
            logger.info(f"[STORAGE LOCAL] Created model folder: {target_dir}")
        except Exception as e:
            logger.error(f"[STORAGE LOCAL ERROR] Failed to create model folder: {e}")

    @classmethod
    def delete_model_folder(cls, model_name: str, background_tasks=None):
        """
        Deletes the model folder on local disk storage.
        """
        if not model_name:
            return
        s_name = sanitize_folder_name(model_name)
        try:
            target_dir = os.path.join(MP_READINESS_DATA_PATH, s_name).replace("\\", "/")
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir, ignore_errors=True)
            logger.info(f"[STORAGE LOCAL] Deleted model folder: {target_dir}")
        except Exception as e:
            logger.error(f"[STORAGE LOCAL ERROR] Failed to delete local model folder: {e}")

    @classmethod
    def reconcile_model_folders(cls, active_model_names: list, background_tasks=None):
        """
        Reconciles model folders on local disk: ensures active models exist and deletes orphaned folders.
        """
        try:
            safe_active = {sanitize_folder_name(n) for n in active_model_names if n}
            for n in active_model_names:
                if n:
                    s_n = sanitize_folder_name(n)
                    os.makedirs(os.path.join(MP_READINESS_DATA_PATH, s_n), exist_ok=True)
            if os.path.exists(MP_READINESS_DATA_PATH):
                for item in os.listdir(MP_READINESS_DATA_PATH):
                    item_path = os.path.join(MP_READINESS_DATA_PATH, item)
                    if os.path.isdir(item_path) and item not in safe_active:
                        shutil.rmtree(item_path, ignore_errors=True)
            logger.info(f"[STORAGE LOCAL RECONCILE] Completed for {len(active_model_names)} models")
        except Exception as e:
            logger.error(f"[STORAGE LOCAL RECONCILE ERROR] {e}")
