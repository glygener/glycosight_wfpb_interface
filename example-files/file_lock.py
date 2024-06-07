import fcntl
from contextlib import contextmanager


# See https://gist.github.com/lonetwin/7b4ccc93241958ff6967
@contextmanager
def locked_open(filename, mode="w"):
    """locked_open(filename, mode='w') -> <open file object>

    Context manager that on entry opens the path `filename`, using `mode`
    (default: `r`), and applies an advisory write lock on the file which
    is released when leaving the context. Yields the open file object for
    use within the context.
    Note: advisory locking implies that all calls to open the file using
    this same api will block for both read and write until the lock is
    acquired. Locking this way will not prevent the file from access using
    any other api/method.
    """
    with open(filename, mode) as fd:
        fcntl.flock(fd, fcntl.LOCK_EX)
        print(f"Acquired lock on {filename}")
        yield fd
        # raw_input('press enter to release lock ')
        print(f"Releasing lock on {filename}")
        fcntl.flock(fd, fcntl.LOCK_UN)
