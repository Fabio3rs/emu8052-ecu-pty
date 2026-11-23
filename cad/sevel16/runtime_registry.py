"""Serialize publishers. Readers only need the atomically replaced revision pointer."""
from contextlib import contextmanager
import os


@contextmanager
def registry_lock(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.publish.lock').open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if handle.tell() == 0:
                handle.write(b'0')
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX)
        yield
