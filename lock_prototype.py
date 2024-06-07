import fcntl
import os
import time


from collections import deque
from threading import Thread

target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./tmp"))
lock_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./locks"))
print(f"reading data from {target_dir}")

valid_lock_files = ["file1.lock", "file2.lock", "file3.lock"]

# Load "Jobs"
job_queue = deque()
for i in range(10):
    job_queue.append(i)
running_jobs = dict()
completed_jobs = dict()

print(f"Loaded {len(job_queue)} jobs")


def printer(deck, running):
    print("Printer - running!")
    while running:
        if deck:
            print(deck.popleft())
    print("Printer: Shutting down ...")


class AtomicBool:
    def __init__(self):
        self.value = True


printer_deck = deque()
running = AtomicBool()

printer_thread = Thread(
    target=printer, args=(printer_deck, running), daemon=True, name="Printer"
)
printer_thread.start()


class LockManager:
    def __init__(self, output_deck):
        self.lockedfiles = {}
        self.deck = output_deck

    def acquire_lock(self):
        for lockname in valid_lock_files:
            # Acquire locks
            lock_path = os.path.join(lock_dir, lockname)
            try:
                fd = open(lock_path)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.lockedfiles[lockname] = fd
                return lockname
            except Exception as e:
                # self.deck.append(f"Exception {e} on {lockname}. Trying next file")
                continue
        return False

    def release_lock(self, lockname):
        fd = self.lockedfiles[lockname]
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except:
            raise


class SleepingContainer(Thread):

    def __init__(self, job_id, lockname, deck):
        super().__init__(daemon=False)
        deck.append(f"Thread {job_id}: Initializing ...")
        self.ticks = 3
        self.job_id = job_id
        self.lockname = lockname
        self.status = "running"
        self.deck = deck
        deck.append(f"Thread {job_id}: Initialized!")

    def run(self):
        self.deck.append(f"Thread {self.job_id}: Running process")
        while self.ticks > 0:
            self.deck.append(f"Thread {self.job_id}: Tick {self.ticks} ...")
            self.ticks -= 1
            time.sleep(1)
        self.deck.append(f"Thread {self.job_id}: Shutting down")
        self.status = "exited"


counter = 0

lock_manager = LockManager(printer_deck)

while len(job_queue) > 0:
    maintenance_set = deque()
    # Check if a lock is available
    lockname = lock_manager.acquire_lock()
    if lockname:
        print(f"---> Lock: Found lockname {lockname}")
        job_id = job_queue.popleft()
        print(f"Popped job ID {job_id}")
        job = SleepingContainer(job_id, lockname, printer_deck)
        print(f"---> Starting job {job}")
        job.start()
        running_jobs[job_id] = job
        continue
    # Check for completed jobs
    for job in running_jobs.values():
        print(f"---> Checking running job {job.job_id}: {job.status}")
        if job.status == "exited":
            job_id = job.job_id
            completed_jobs[job_id] = "completed output"
            # Release resources
            lock_manager.release_lock(job.lockname)
            job.join()
            maintenance_set.append(job_id)
    while maintenance_set:
        running_jobs.pop(maintenance_set.popleft())
    print(
        f"Jobs launched. Now running {len(running_jobs.keys())} jobs; sleeping while we wait"
    )
    time.sleep(1)

# All jobs launched ... wait for completion
while running_jobs:
    for job in running_jobs.values():
        if job.status == "exited":
            job_id = job.job_id
            completed_jobs[job_id] = "completed output"
            lock_manager.release_lock(job.lockname)
            job.join()
            maintenance_set.append(job_id)
    while maintenance_set:
        running_jobs.pop(maintenance_set.popleft())

running = False
