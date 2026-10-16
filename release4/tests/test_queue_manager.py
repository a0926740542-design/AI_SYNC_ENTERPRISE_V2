import time
from app.queue_manager import QueueManager
def callback(filepath): print("CALLBACK :", filepath)
def main():
    q = QueueManager(callback)
    q.start()
    q.put("TEST1.txt")
    q.put("TEST1.txt")
    q.put("TEST2.txt")
    time.sleep(3)
    q.stop()
if __name__ == "__main__": main()
