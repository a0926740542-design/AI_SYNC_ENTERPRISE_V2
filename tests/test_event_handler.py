from app.event_handler import EventHandler


class FakeQueue:

    def __init__(self):
        self.files = []

    def put(self, filepath):
        self.files.append(filepath)


class FakeEvent:

    def __init__(self, path, is_directory=False):

        self.src_path = path
        self.dest_path = path
        self.is_directory = is_directory


def main():

    queue = FakeQueue()

    handler = EventHandler(queue)

    handler.on_created(FakeEvent(r"C:\WORK\A.txt"))

    handler.on_modified(FakeEvent(r"C:\WORK\B.txt"))

    handler.on_moved(FakeEvent(r"C:\WORK\C.txt"))

    print(queue.files)


if __name__ == "__main__":
    main()