from types import SimpleNamespace
from app.event_handler import EventHandler
class Router:
    def __init__(self): self.events = []
    def route(self, event): self.events.append(event)
def test_event_handler_routes_supported_events():
    router = Router()
    handler = EventHandler(router)
    for method in (handler.on_created, handler.on_modified, handler.on_moved):
        event = SimpleNamespace(is_directory=False, src_path="example.txt", dest_path="moved.txt")
        method(event)
    assert len(router.events) == 3
