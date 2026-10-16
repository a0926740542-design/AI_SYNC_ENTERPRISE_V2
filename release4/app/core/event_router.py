"""Route file events to debounced worker."""
from pathlib import Path
IGNORED_EXTENSIONS = {'.bak', '.sv$', '.dwl', '.dwl2', '.tmp'}
class EventRouter:
    def __init__(self, worker_pool, deduplicator=None):
        self.worker_pool = worker_pool
        self.deduplicator = deduplicator
    def route(self, event):
        if event.is_directory or event.event_type == 'deleted':
            return False
        filepath = str(Path(event.dest_path if event.event_type == 'moved' else event.src_path).resolve())
        if Path(filepath).suffix.lower() in IGNORED_EXTENSIONS:
            return False
        return self.worker_pool.submit(filepath)
