"""Create complete output files without replacing any existing directory entry."""
import os
from pathlib import Path
import tempfile


def write_new(path, writer):
    """Publish through a hard link, atomically failing if destination exists."""
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.lutphoto-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def write_bytes_new(path, raw):
    write_new(path, lambda stream: stream.write(raw))
