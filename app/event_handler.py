from watchdog.events import FileSystemEventHandler


class EventHandler(FileSystemEventHandler):
    """
    Enterprise Event Handler

    職責：
    - 接收 Watchdog 事件
    - 過濾資料夾事件
    - 將檔案加入 Queue
    """

    def __init__(self, queue_manager):
        self.queue = queue_manager

    def on_created(self, event):

        if event.is_directory:
            return

        self.queue.put(event.src_path)

    def on_modified(self, event):

        if event.is_directory:
            return

        self.queue.put(event.src_path)

    def on_moved(self, event):

        if event.is_directory:
            return

        self.queue.put(event.dest_path)