import os
import logging
from backend.core.config import (
    STORAGE_USERDATA_PROVIDERS,
    STORAGE_DB_PROVIDERS,
    SYNC_MODE,
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
        Saves document HTML content across configured providers (LOCAL, GDRIVE, SUPABASE).
        Supports ASYNC non-blocking background synchronization.
        """
        primary_saved = False

        # 1. LOCAL Provider Execution
        if "LOCAL" in STORAGE_USERDATA_PROVIDERS or not STORAGE_USERDATA_PROVIDERS:
            try:
                local_file_path = cls.get_local_html_path(model_name, team, level_1, level_2, version_name)
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                with open(local_file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                primary_saved = True
                logger.info(f"[STORAGE LOCAL] Saved content.html successfully: {local_file_path}")
            except Exception as e:
                logger.error(f"[STORAGE LOCAL ERROR] Failed to save local file: {e}")

        # 2. GDRIVE Provider Execution
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            from backend.core.gdrive_storage import upload_html_content_to_gdrive
            rel_path = f"{model_name}/{team}/{level_1}/{level_2}/{version_name}/content.html"
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(upload_html_content_to_gdrive, rel_path, html_content)
                logger.info(f"[STORAGE GDRIVE] Scheduled background upload for {rel_path}")
            else:
                try:
                    upload_html_content_to_gdrive(rel_path, html_content)
                except Exception as e:
                    logger.error(f"[STORAGE GDRIVE ERROR] Sync failed: {e}")

        # 3. SUPABASE Provider Execution (Placeholder / SDK Hook)
        if "SUPABASE" in STORAGE_USERDATA_PROVIDERS:
            rel_path = f"{model_name}/{team}/{level_1}/{level_2}/{version_name}/content.html"
            def _supabase_upload(r_path, content):
                logger.info(f"[STORAGE SUPABASE BUCKET] Placeholder sync for {r_path}")

            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(_supabase_upload, rel_path, html_content)
            else:
                _supabase_upload(rel_path, html_content)

        return primary_saved

    @classmethod
    def read_document_html(cls, model_name: str, team: str, level_1: str, level_2: str, version_name: str) -> str:
        """
        Reads document HTML content. Tries Local first, falls back to GDrive/Supabase if needed.
        """
        local_file_path = cls.get_local_html_path(model_name, team, level_1, level_2, version_name)
        if os.path.exists(local_file_path):
            with open(local_file_path, "r", encoding="utf-8") as f:
                return f.read()

        # Fallback to Google Drive if configured
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            try:
                from backend.core.gdrive_storage import read_html_content_from_gdrive
                rel_path = f"{model_name}/{team}/{level_1}/{level_2}/{version_name}/content.html"
                content = read_html_content_from_gdrive(rel_path)
                if content:
                    return content
            except Exception as e:
                logger.error(f"[STORAGE READ FALLBACK ERROR] GDrive read failed: {e}")

        return ""

    @classmethod
    def sync_database(cls, background_tasks=None):
        """
        Triggers database synchronization (e.g., to Google Drive or Supabase).
        """
        if "GDRIVE" in STORAGE_DB_PROVIDERS:
            from backend.core.gdrive_storage import sync_database_to_gdrive
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(sync_database_to_gdrive)
                logger.info("[STORAGE DB GDRIVE] Scheduled background DB sync")
            else:
                try:
                    sync_database_to_gdrive()
                except Exception as e:
                    logger.error(f"[STORAGE DB GDRIVE ERROR] Sync failed: {e}")


        if "SUPABASE" in STORAGE_DB_PROVIDERS:
            def _supabase_db_sync():
                logger.info("[STORAGE DB SUPABASE] Placeholder Postgres DB sync")

            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(_supabase_db_sync)
            else:
                _supabase_db_sync()

    @classmethod
    def create_model_folder(cls, model_name: str, background_tasks=None):
        """
        Creates the model root folder across configured providers (LOCAL, GDRIVE, SUPABASE).
        """
        if not model_name:
            return
            
        s_name = sanitize_folder_name(model_name)
        
        # 1. LOCAL Provider
        if "LOCAL" in STORAGE_USERDATA_PROVIDERS or not STORAGE_USERDATA_PROVIDERS:
            try:
                target_dir = os.path.join(MP_READINESS_DATA_PATH, s_name).replace("\\", "/")
                os.makedirs(target_dir, exist_ok=True)
                logger.info(f"[STORAGE LOCAL] Created model folder: {target_dir}")
            except Exception as e:
                logger.error(f"[STORAGE LOCAL ERROR] Failed to create model folder: {e}")

        # 2. GDRIVE Provider
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            from backend.core.gdrive_storage import create_folder_on_gdrive
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(create_folder_on_gdrive, s_name)
            else:
                try:
                    create_folder_on_gdrive(s_name)
                except Exception as e:
                    logger.error(f"[STORAGE GDRIVE ERROR] Failed to create model folder on Drive: {e}")

        # 3. SUPABASE Provider Placeholder
        if "SUPABASE" in STORAGE_USERDATA_PROVIDERS:
            def _supabase_mkdir(m_name):
                logger.info(f"[STORAGE SUPABASE BUCKET] Placeholder mkdir for model: {m_name}")
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(_supabase_mkdir, s_name)
            else:
                _supabase_mkdir(s_name)

    @classmethod
    def delete_model_folder(cls, model_name: str, background_tasks=None):
        """
        Deletes/trashes the model folder across configured providers (LOCAL, GDRIVE, SUPABASE).
        """
        if not model_name:
            return

        s_name = sanitize_folder_name(model_name)

        # 1. LOCAL Provider
        if "LOCAL" in STORAGE_USERDATA_PROVIDERS or not STORAGE_USERDATA_PROVIDERS:
            try:
                import shutil
                target_dir = os.path.join(MP_READINESS_DATA_PATH, s_name).replace("\\", "/")
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir, ignore_errors=True)
                logger.info(f"[STORAGE LOCAL] Deleted model folder: {target_dir}")
            except Exception as e:
                logger.error(f"[STORAGE LOCAL ERROR] Failed to delete local model folder: {e}")

        # 2. GDRIVE Provider
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            from backend.core.gdrive_storage import delete_folder_on_gdrive
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(delete_folder_on_gdrive, s_name)
            else:
                try:
                    delete_folder_on_gdrive(s_name)
                except Exception as e:
                    logger.error(f"[STORAGE GDRIVE ERROR] Failed to delete model folder on Drive: {e}")

        # 3. SUPABASE Provider Placeholder
        if "SUPABASE" in STORAGE_USERDATA_PROVIDERS:
            def _supabase_rmdir(m_name):
                logger.info(f"[STORAGE SUPABASE BUCKET] Placeholder rmdir for model: {m_name}")
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(_supabase_rmdir, s_name)
            else:
                _supabase_rmdir(s_name)

    @classmethod
    def reconcile_model_folders(cls, active_model_names: list, background_tasks=None):
        """
        Full scan and reconciliation across configured providers (LOCAL, GDRIVE, SUPABASE).
        Ensures active models exist and deletes orphaned folders.
        """
        # 1. LOCAL Provider Execution
        if "LOCAL" in STORAGE_USERDATA_PROVIDERS or not STORAGE_USERDATA_PROVIDERS:
            try:
                import shutil
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

        # 2. GDRIVE Provider Execution
        if "GDRIVE" in STORAGE_USERDATA_PROVIDERS:
            from backend.core.gdrive_storage import reconcile_gdrive_model_folders
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(reconcile_gdrive_model_folders, active_model_names)
            else:
                try:
                    reconcile_gdrive_model_folders(active_model_names)
                except Exception as e:
                    logger.error(f"[STORAGE GDRIVE RECONCILE ERROR] {e}")

        # 3. SUPABASE Provider Execution (Placeholder)
        if "SUPABASE" in STORAGE_USERDATA_PROVIDERS:
            def _supabase_reconcile(models):
                logger.info(f"[STORAGE SUPABASE BUCKET] Placeholder reconcile for models: {models}")
            if SYNC_MODE == "ASYNC" and background_tasks is not None:
                background_tasks.add_task(_supabase_reconcile, active_model_names)
            else:
                _supabase_reconcile(active_model_names)



