"""Private POSIX storage and bounded payload sinks; no transport or device code."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time

CHUNK = 65536
ROOT = Path(__file__).resolve().parents[1]
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')) + '\n').encode()


def _private(info, directory=False):
    if (not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or info.st_uid != os.geteuid() or info.st_mode & 0o077
            or not directory and info.st_nlink != 1):
        raise ValueError('Expected private owned storage')


def _same(a, b):
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def _parent(path):
    path = Path(path).absolute()
    if any(p in ('.', '..') for p in path.parts) or path == ROOT or ROOT in path.parents:
        raise ValueError('New storage must be outside the repository')
    fd = os.open(path.anchor, DIR_FLAGS)
    try:
        for part in path.parts[1:-1]:
            new = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd); fd = new
            info = os.fstat(fd)
            if (info.st_uid not in (0, os.geteuid())
                    or info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX):
                raise ValueError('Untrusted ancestor directory')
        info = os.fstat(fd)
        if info.st_uid != os.geteuid() or info.st_mode & 0o022:
            raise ValueError('Final parent must be owned and not shared writable')
        return path, fd
    except BaseException:
        os.close(fd)
        raise


class Budget:
    def __init__(self, limit, *, seconds=1200, clock=time.monotonic):
        if type(limit) is not int or limit <= 0 or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('Finite positive payload budget required')
        self.limit, self.used, self.clock = limit, 0, clock
        self.deadline = clock() + seconds

    def check(self):
        if self.clock() >= self.deadline:
            raise TimeoutError('Simulation payload deadline expired')

    def accept(self, size):
        self.check()
        if self.used + size > self.limit:
            raise ValueError('Total payload budget exceeded')
        self.used += size


class Sink:
    """Reject before hash/write; retain any earlier partial file on failure."""
    def __init__(self, limit, *, exact=None, budget=None, store=None, relative=None):
        if type(limit) is not int or limit <= 0 or exact is not None and (type(exact) is not int or not 0 < exact <= limit):
            raise ValueError('Invalid payload bound')
        self.limit, self.exact, self.budget = limit, exact, budget
        self.size, self.digest, self.closed = 0, hashlib.sha256(), False
        self.store, self.relative, self.fd = store, relative, None
        if store is not None:
            self.fd = store._new(relative)

    def write(self, raw):
        if self.closed or type(raw) is not bytes or not 0 < len(raw) <= CHUNK or self.size + len(raw) > self.limit:
            raise ValueError('Invalid or oversized payload chunk')
        if self.budget is not None:
            self.budget.accept(len(raw))
        if self.fd is not None:
            view = memoryview(raw)
            while view:
                n = os.write(self.fd, view)
                if not 0 < n <= len(view):
                    raise OSError('Incomplete host write')
                view = view[n:]
        self.digest.update(raw); self.size += len(raw)
        return len(raw)

    def finish(self):
        if self.closed or not self.size or self.exact is not None and self.size != self.exact:
            raise ValueError('Incomplete payload')
        if self.budget is not None:
            self.budget.check()
        result = {'bytes': self.size, 'sha256': self.digest.hexdigest()}
        if self.fd is not None:
            os.fsync(self.fd)
            self.store._verify(self.relative, self.fd, result)
            os.fsync(self.store._folder(self.relative)[0])
        self.close()
        return result

    def close(self):
        if self.fd is not None:
            os.close(self.fd); self.fd = None
        self.closed = True


class Store:
    """One new directory, descriptor-relative files, append-only event chain."""
    def __init__(self, path):
        self.fds, self.lock, self.seq, self.head = {}, None, 0, '0' * 64
        self.documents = {}
        self.path, self.parent = _parent(path)
        try:
            os.mkdir(self.path.name, 0o700, dir_fd=self.parent)
            self.fds[''] = os.open(self.path.name, DIR_FLAGS, dir_fd=self.parent)
            self.check()
            self.lock = self._new('session.lock')
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(self.lock)
            for name in ('source', 'evidence', 'resources', 'events'):
                os.mkdir(name, 0o700, dir_fd=self.fds[''])
                self.fds[name] = os.open(name, DIR_FLAGS, dir_fd=self.fds[''])
            self.check()
            for fd in self.fds.values(): os.fsync(fd)
            os.fsync(self.parent)
        except BaseException:
            self.close()
            raise

    def check(self):
        root = self.fds['']
        if not _same(os.fstat(root), os.stat(self.path.name, dir_fd=self.parent, follow_symlinks=False)):
            raise ValueError('Storage root changed')
        for name, fd in self.fds.items():
            _private(os.fstat(fd), True)
            if name and not _same(os.fstat(fd), os.stat(name, dir_fd=root, follow_symlinks=False)):
                raise ValueError('Storage directory changed')
        if self.lock is not None:
            info = os.fstat(self.lock); _private(info)
            if not _same(info, os.stat('session.lock', dir_fd=root, follow_symlinks=False)):
                raise ValueError('Session lock entry changed')

    def _folder(self, relative):
        if type(relative) is not str:
            raise ValueError('Invalid material name')
        parts = relative.split('/')
        if len(parts) > 2 or any(not p or p in ('.', '..') or '\\' in p or any(ord(c) < 32 for c in p) for p in parts):
            raise ValueError('Invalid material name')
        folder, name = ('', parts[0]) if len(parts) == 1 else parts
        if folder not in self.fds:
            raise ValueError('Unowned material folder')
        return self.fds[folder], name

    def require_space(self, minimum):
        self.check()
        if type(minimum) is not int or minimum <= 0:
            raise ValueError('Positive storage budget required')
        info = os.fstatvfs(self.fds[''])
        if info.f_frsize <= 0 or info.f_bavail < 0 or info.f_bavail * info.f_frsize < minimum:
            raise OSError('Insufficient available storage')

    def _new(self, relative):
        self.check(); folder, name = self._folder(relative)
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=folder)
        try:
            _private(os.fstat(fd))
            if not _same(os.fstat(fd), os.stat(name, dir_fd=folder, follow_symlinks=False)):
                raise ValueError('Material entry changed')
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _verify(self, relative, fd, expected):
        self.check(); folder, name = self._folder(relative)
        before = os.fstat(fd); _private(before)
        if not _same(before, os.stat(name, dir_fd=folder, follow_symlinks=False)):
            raise ValueError('Material entry changed')
        os.lseek(fd, 0, os.SEEK_SET); digest = hashlib.sha256(); size = 0
        while True:
            raw = os.read(fd, CHUNK)
            if not raw: break
            size += len(raw)
            if size > expected['bytes']: raise ValueError('Material grew during verification')
            digest.update(raw)
        after = os.fstat(fd)
        if (size != expected['bytes'] or digest.hexdigest() != expected['sha256']
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError('Material readback differs')
        _private(after); self.check()
        if not _same(after, os.stat(name, dir_fd=folder, follow_symlinks=False)):
            raise ValueError('Material changed after readback')

    def read(self, relative, expected):
        self.check(); folder, name = self._folder(relative)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        try:
            self._verify(relative, fd, expected)
            os.lseek(fd, 0, os.SEEK_SET)
            raw = bytearray()
            while len(raw) <= expected['bytes']:
                block = os.read(fd, min(CHUNK, expected['bytes'] + 1 - len(raw)))
                if not block: break
                raw.extend(block)
            if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
                raise ValueError('Material changed while decoding')
            return bytes(raw)
        finally:
            os.close(fd)

    def verify(self, relative, expected):
        self.check(); folder, name = self._folder(relative)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        try:
            self._verify(relative, fd, expected)
        finally:
            os.close(fd)

    def put(self, relative, raw, *, limit=131072):
        sink = Sink(limit, exact=len(raw), store=self, relative=relative)
        try:
            for at in range(0, len(raw), CHUNK): sink.write(raw[at:at + CHUNK])
            result = sink.finish()
            self.documents[relative] = result
            return result
        finally:
            sink.close()

    def event(self, event, **details):
        if self.seq >= 512: raise ValueError('Event limit exceeded')
        raw = encoded({'seq': self.seq, 'previous_sha256': self.head, 'event': event, 'details': details})
        result = self.put(f'events/{self.seq:08d}.json', raw, limit=16384)
        self.head = result['sha256']; self.seq += 1

    def close(self):
        for fd in self.fds.values(): os.close(fd)
        self.fds.clear()
        if self.lock is not None:
            os.close(self.lock); self.lock = None
        if getattr(self, 'parent', None) is not None:
            os.close(self.parent); self.parent = None
