#!/usr/bin/env python3
"""Opt-in cache of original-instruction results for validators (TEST-SPEED-001).

A validator compares the pinned original client code (run under Unicorn) with the reconstructed C, case by case.
The pinned original never changes, so the ORIGINAL side of a case is a pure function of

  (the pins' sha256, the validator, the Python code that drives the original side, the case input)

and can be reused. Only that side is ever cached: the C side runs fresh for every case and is compared with the
cached original result exactly as with a fresh one, so the cache cannot hide a C change. The key includes the
sha256 of every Python file the validator imports or names (scripts/affected.py closure), the Unicorn version and
every pin's sha256, so any change to the harness, the world setup or an input starts a fresh cache.

The cache is off unless MU_VALIDATOR_CACHE names a directory (``run_validators.py --cache`` sets it to
~/Documents/MTM/mu-mac-tools/native/cache/validators; ``--no-cache`` clears it). Files:
<dir>/<validator>/<key>.pickle.xz, one per key. Several keys of a name are kept (TEST-SPEED-003), so a lane branch
and main with different harness versions do not evict each other: loading a key marks it used (mtime), and a save
keeps the KEEP most recently used keys per name (MU_VALIDATOR_CACHE_KEYS, default 4) and then removes the least
recently used files of the whole directory until it is at most MAX_MB (MU_VALIDATOR_CACHE_MAX_MB, default 250).
The key file just written is never removed, and a file is only ever returned for the key stored inside it.
A save holds a per-name lock (fcntl) and merges the entries another process saved under the same key since this
one loaded, so two --jobs workers sharing a name (gen_item_bodies) neither corrupt nor drop each other's entries;
the file is replaced atomically, so a reader sees the old or the new file, never a partial one.
The cache file is local and written only by this module (pickle keeps the exact tuples and ints the
comparison needs).

  cache = original_cache.active()            # the validator's cache (a no-op object when disabled)
  result = cache.get('bodies', case, lambda: run_the_original(case))
  original_cache.named('gen_item_bodies', Path(__file__))   # one cache shared by every validator using it
"""
from __future__ import annotations

import atexit
import contextlib
import fcntl
import hashlib
import json
import lzma
import os
from pathlib import Path
import pickle
import sys
import tempfile
import time

ENV = 'MU_VALIDATOR_CACHE'
DEFAULT = Path.home() / 'Documents' / 'MTM' / 'mu-mac-tools' / 'native' / 'cache' / 'validators'
FORMAT = 1                       # part of every key: a new storage format starts fresh keys
KEEP_ENV, KEEP = 'MU_VALIDATOR_CACHE_KEYS', 4          # keys kept per name (LRU by mtime)
MAX_ENV, MAX_MB = 'MU_VALIDATOR_CACHE_MAX_MB', 250     # size cap of the whole cache directory
SUFFIX = '.pickle.xz'
STALE_TMP = 6 * 3600             # a writer's temporary file older than this was left by a killed process


def _setting(env: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(env, '') or default))
    except ValueError:
        return default


@contextlib.contextmanager
def _locked(path: Path):
    """An exclusive advisory lock on PATH (created if missing); released when the block ends or the process dies."""
    with open(path, 'a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _stat(path: Path):
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_ino, st.st_size)   # a save replaces the file (new inode); a reader's touch changes neither


def _read(path: Path, key: str) -> dict | None:
    """The entries of PATH if it stores KEY; None if it is missing, unreadable or for another key."""
    return _read_stat(path, key)[0]


def _read_stat(path: Path, key: str):
    """(_read, _stat) of the same file: the stat of the file object actually read, so a save by another worker
    between reading and stat-ing cannot make a reader believe it has entries it never loaded (TEST-SPEED-004)."""
    try:
        with open(path, 'rb') as raw:
            st = os.fstat(raw.fileno())
            seen = (st.st_ino, st.st_size)
            try:
                with lzma.open(raw, 'rb') as handle:
                    stored = pickle.load(handle)
                if stored.get('key') == key:
                    return stored['entries'], seen
            except Exception:   # a damaged file is a miss, never an error
                pass
            return None, seen
    except OSError:
        return None, None


def _files(folder: Path) -> list[tuple[float, int, Path]]:
    """(mtime, size, path) of FOLDER's key files, most recently used first; files removed meanwhile are skipped."""
    out = []
    try:
        children = list(folder.iterdir())
    except OSError:
        return out
    for child in children:
        if child.name.endswith(SUFFIX):
            try:
                st = child.stat()
            except OSError:
                continue
            out.append((st.st_mtime, st.st_size, child))
    return sorted(out, key=lambda f: (-f[0], f[2].name))


def _unlink(path: Path):
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def prune(directory: Path, keep_path: Path | None = None, keep: int | None = None, max_bytes: int | None = None):
    """Keep the KEEP most recently used keys of every name, then drop the least recently used files of the whole
    DIRECTORY until it holds at most MAX_BYTES. KEEP_PATH (the file just written) is never removed."""
    keep = keep or _setting(KEEP_ENV, KEEP)
    max_bytes = max_bytes if max_bytes is not None else _setting(MAX_ENV, MAX_MB) << 20
    directory.mkdir(parents=True, exist_ok=True)
    now = time.time()
    with _locked(directory / '.lock'):
        remaining = []
        for folder in sorted(p for p in directory.iterdir() if p.is_dir()):
            for child in list(folder.iterdir()):
                if child.name.startswith('.tmp-'):
                    try:
                        if now - child.stat().st_mtime > STALE_TMP:
                            _unlink(child)
                    except OSError:
                        pass
            files = _files(folder)
            kept = [f for f in files if f[2] == keep_path]
            for f in files:
                if f[2] == keep_path:
                    continue
                if len(kept) < keep:
                    kept.append(f)
                else:
                    _unlink(f[2])
            remaining += kept
        total = sum(f[1] for f in remaining)
        for mtime, size, path in sorted(remaining, key=lambda f: (f[0], str(f[2]))):
            if total <= max_bytes:
                break
            if path != keep_path:
                _unlink(path)
                total -= size


def canonical(value) -> str:
    """A stable text form of a case input (dict keys sorted; tuples, lists, ints, floats, bytes, None)."""
    if isinstance(value, dict):
        return '{' + ','.join(f'{canonical(k)}:{canonical(v)}' for k, v in sorted(value.items(), key=lambda kv: repr(kv[0]))) + '}'
    if isinstance(value, (list, tuple)):
        inner = ','.join(canonical(v) for v in value)
        return f'[{inner}]' if isinstance(value, list) else f'({inner})'
    if isinstance(value, float):
        return float.hex(value)
    if isinstance(value, (int, str, bytes, bool)) or value is None:
        return repr(value)
    raise TypeError(f'original_cache: no canonical form for {type(value).__name__}')


def code_hash(script: Path) -> dict[str, str]:
    """sha256 of every Python file in SCRIPT's import/name closure (repository files only)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import affected
    deps = affected.python_deps(script.resolve())
    out = {}
    for name in sorted(deps.files):
        path = affected.ROOT / name
        if name.endswith('.py') and path.is_file():
            out[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not out:   # a script outside the repository: itself
        out[script.name] = hashlib.sha256(script.read_bytes()).hexdigest()
    return out


class Disabled:
    enabled = False
    hits = misses = 0

    def get(self, family, case, compute):
        return compute()

    def save(self):
        pass


class Cache:
    enabled = True

    def __init__(self, directory: Path, validator: str, script: Path, extra: dict | None = None):
        import pins
        try:
            import unicorn
            unicorn_version = unicorn.__version__
        except ImportError:   # pragma: no cover - every original-side validator needs Unicorn
            unicorn_version = None
        identity = {'format': FORMAT, 'validator': validator, 'python': sys.version_info[:2],
                    'unicorn': unicorn_version, 'pins': {n: p.sha256 for n, p in sorted(pins.PINS.items())},
                    'code': code_hash(script), 'extra': extra or {}}
        self.key = hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()[:24]
        self.folder = directory / validator
        self.path = self.folder / f'{self.key}.pickle.xz'
        self.directory = directory
        self.data: dict[str, object] = {}
        self.seen = None   # (inode, size) of the file as loaded, to notice another writer's save
        if self.path.is_file():
            data, self.seen = _read_stat(self.path, self.key)
            self.data = data or {}
            if self.data:
                try:
                    os.utime(self.path)   # mark the key used: the per-name and size limits drop the least recent
                except OSError:
                    pass
        self.loaded = len(self.data)
        self.hits = self.misses = 0
        self.dirty = False

    def get(self, family: str, case, compute):
        key = f'{family}\0{canonical(case)}'
        if key in self.data:
            self.hits += 1
            return self.data[key]
        value = compute()
        pickle.dumps(value)   # refuse what cannot be stored before it is used
        self.data[key] = value
        self.misses += 1
        self.dirty = True
        return value

    def save(self):
        print(f'original_cache: {self.folder.name}: {self.hits} hits, {self.misses} misses '
              f'({self.loaded} loaded) {self.path}', file=sys.stderr, flush=True)
        if not self.dirty:
            return
        self.folder.mkdir(parents=True, exist_ok=True)
        with _locked(self.folder / '.lock'):
            current = _stat(self.path)
            if current is not None and current != self.seen:   # another worker saved this key since we loaded
                theirs = _read(self.path, self.key)
                if theirs:
                    theirs.update(self.data)
                    self.data = theirs
            fd, tmp = tempfile.mkstemp(dir=self.folder, prefix='.tmp-', suffix='.xz')
            os.close(fd)
            try:
                with lzma.open(tmp, 'wb', preset=6) as handle:
                    pickle.dump({'key': self.key, 'entries': self.data}, handle, protocol=pickle.HIGHEST_PROTOCOL)
                os.replace(tmp, self.path)
            except BaseException:
                _unlink(Path(tmp))
                raise
            self.seen = _stat(self.path)
            self.dirty = False
        prune(self.directory, keep_path=self.path)


_caches: dict[str, Cache | Disabled] = {}


def named(name: str, script: Path) -> Cache | Disabled:
    """A cache shared by every validator that runs SCRIPT's original side (e.g. gen_item_bodies' samples),
    keyed by SCRIPT's own code closure; saved at exit. Disabled unless MU_VALIDATOR_CACHE is set."""
    if name not in _caches:
        root = os.environ.get(ENV, '').strip()
        if not root:
            _caches[name] = Disabled()
        else:
            _caches[name] = Cache(Path(root).expanduser(), name, Path(script))
            atexit.register(_caches[name].save)
    return _caches[name]


def active() -> Cache | Disabled:
    """The cache of the running validator (named after the __main__ script, keyed by its code closure)."""
    main = getattr(sys.modules.get('__main__'), '__file__', None)
    if not main:
        return _caches.setdefault('', Disabled())
    return named(Path(main).stem, Path(main))
