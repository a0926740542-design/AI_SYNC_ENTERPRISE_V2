import time
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "app"))

from queue_manager import QueueManager


def callback(filepath):

    print("CALLBACK :", filepath)


def main():

    q = QueueManager(callback)

    q.start()

    q.put(r"C:\WORK\TEST1.txt")
    q.put(r"C:\WORK\TEST1.txt")
    q.put(r"C:\WORK\TEST1.txt")
    q.put(r"C:\WORK\TEST2.txt")

    time.sleep(3)

    q.stop()


if __name__ == "__main__":
    main()