import queue
import threading
import logging
from backend.core.gdrive_storage import (
    create_folder_on_gdrive,
    delete_folder_on_gdrive,
    reconcile_gdrive_model_folders,
    upload_html_content_to_gdrive,
    sync_database_to_gdrive,
    upload_file_to_gdrive
)

logger = logging.getLogger(__name__)

class GDriveQueueManager:
    def __init__(self):
        self._queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("[GDRIVE QUEUE] Background worker thread started successfully!")

    def enqueue(self, func, *args, **kwargs):
        self._queue.put((func, args, kwargs))

    def _worker_loop(self):
        while True:
            try:
                func, args, kwargs = self._queue.get()
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"[GDRIVE QUEUE WORKER ERROR] {func.__name__} failed: {e}")
                finally:
                    self._queue.task_done()
            except Exception as e:
                logger.error(f"[GDRIVE QUEUE LOOP ERROR] {e}")

gdrive_worker_queue = GDriveQueueManager()
