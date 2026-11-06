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
<dir>/<validator>/<key>.pickle.xz, one per key; older keys of the same validator are deleted when a new one is
written. The cache file is local and written only by this module (pickle keeps the exact tuples and ints the
comparison needs).

  cache = original_cache.active()            # the validator's cache (a no-op object when disabled)
  result = cache.get('bodies', case, lambda: run_the_original(case))
  original_cache.named('gen_item_bodies', Path(__file__))   # one cache shared by every validator using it
"""
from __future__ import annotations

import atexit
import hashlib
import json
import lzma
import os
from pathlib import Path
import pickle
import sys
import tempfile

ENV = 'MU_VALIDATOR_CACHE'
DEFAULT = Path.home() / 'Documents' / 'MTM' / 'mu-mac-tools' / 'native' / 'cache' / 'validators'
FORMAT = 1


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
        self.data: dict[str, object] = {}
        if self.path.is_file():
            try:
                with lzma.open(self.path, 'rb') as handle:
                    stored = pickle.load(handle)
                if stored.get('key') == self.key:
                    self.data = stored['entries']
            except (OSError, EOFError, lzma.LZMAError, pickle.UnpicklingError, KeyError):
                self.data = {}
        self.loaded = len(self.data)
        self.hits = self.misses = 0

    def get(self, family: str, case, compute):
        key = f'{family}\0{canonical(case)}'
        if key in self.data:
            self.hits += 1
            return self.data[key]
        value = compute()
        pickle.dumps(value)   # refuse what cannot be stored before it is used
        self.data[key] = value
        self.misses += 1
        return value

    def save(self):
        print(f'original_cache: {self.folder.name}: {self.hits} hits, {self.misses} misses '
              f'({self.loaded} loaded) {self.path}', file=sys.stderr, flush=True)
        if not self.misses:
            return
        self.folder.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.folder, prefix='.tmp-', suffix='.xz')
        os.close(fd)
        with lzma.open(tmp, 'wb', preset=6) as handle:
            pickle.dump({'key': self.key, 'entries': self.data}, handle, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, self.path)
        for old in self.folder.iterdir():   # one key per validator: drop older harness versions
            if old.name.endswith('.pickle.xz') and old.name != self.path.name:
                old.unlink()


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
