from watchdog.events import FileSystemEventHandler
class WatchdogHandler(FileSystemEventHandler):
    def __init__(self, router):
        super().__init__()
        self.router = router
    def on_created(self, event):
        self.router.route(event)
    def on_modified(self, event):
        self.router.route(event)
    def on_moved(self, event):
        self.router.route(event)
