from watchdog.observers import Observer
class ObserverManager:
    def __init__(self):
        self._observer = Observer()
        self._started = False
    @property
    def observer(self):
        return self._observer
    @property
    def running(self):
        return self._started
    def schedule(self, handler, path, recursive=True):
        if self._started: raise RuntimeError('Schedule before starting observer')
        self._observer.schedule(handler, str(path), recursive=recursive)
    def start(self):
        if not self._started:
            self._observer.start()
            self._started = True
    def stop(self):
        if self._started:
            self._observer.stop()
            self._observer.join()
            self._started = False
