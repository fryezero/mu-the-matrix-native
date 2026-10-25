"""The pinned inputs of the validators: every capture digest and default input path, in one place.

VERIFY-HARNESS-001. Every scripts/validate_*.py and scripts/*_machine.py takes its whole-input pins (the
restored text, the second image section, the trig dispatch flag, the CPU feature word, the third-section
captures, the client executable, the private model manifest, the langread snapshots) from this module
instead of pasting digests and paths. tests/test_pins.py fails when a digest registered here appears in
another script.

Where an input is found:

* an explicit path (a command-line option) always wins;
* then the pin's environment variables, first set one wins (MU_CLIENT_TEXT, MU_IMAGE_DATA, ...; the same
  names the validators and tests used before, so existing recipes keep working);
* then the pin's default location: under the evidence directory, which is ``MU_EVIDENCE_DIR`` when set and
  ``<repository>/evidence`` otherwise (a worktree points ``MU_EVIDENCE_DIR`` at the main checkout's
  ignored ``evidence/``); under the repository for repository-relative pins; under ``MU_SNAPSHOT_DIR``
  for langread snapshots, which have no default at all when it is unset.

A missing input is an explicit error (``PinMissing``, which names the pin, the path tried and the variables
that move it), never a silent fallback to another directory. Bytes that differ from the pin raise
``PinMismatch``. Both subclass the built-in errors the old per-script loaders raised (``FileNotFoundError``,
``ValueError``), so callers that catch those keep working.

What is not here: digests of single client routines (the ``ROUTINES``/``BODIES`` tables of each family) stay
with the family that defines the routine, because they are part of what the family compares, not inputs
it loads. Digests of installed game files a family expects (model_edge's sample corpus) stay there too.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVIDENCE_ENV = 'MU_EVIDENCE_DIR'
SNAPSHOT_ENV = 'MU_SNAPSHOT_DIR'


class PinError(Exception):
    """A pinned input is missing or differs from its pin."""


class PinMissing(PinError, FileNotFoundError):
    """The pinned input is not where it should be (or no location is configured)."""


class PinMismatch(PinError, ValueError):
    """The input's size or SHA-256 differs from the pin."""


def evidence_dir() -> Path:
    """MU_EVIDENCE_DIR, else the repository's own (ignored) evidence directory."""
    value = os.environ.get(EVIDENCE_ENV)
    return Path(value).expanduser() if value else REPO / 'evidence'


def snapshot_dir() -> Path | None:
    value = os.environ.get(SNAPSHOT_ENV)
    return Path(value).expanduser() if value else None


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Pin:
    """One pinned input: its identity (SHA-256, size) and where it is found by default.

    ``whole`` pins cover a whole file; region pins (``whole=False``) cover ``size`` bytes at ``offset`` of a
    larger file (the neighbour table inside a third-section read)."""
    name: str
    sha256: str
    size: int | None
    relative: str | None
    root: str = 'evidence'        # 'evidence', 'repo' or 'snapshot'
    env: tuple[str, ...] = ()
    offset: int = 0
    whole: bool = True
    base: int | None = None       # client address of the first pinned byte, when it is client memory
    what: str = ''

    # ---- where -------------------------------------------------------------------------------
    def root_dir(self) -> Path | None:
        if self.root == 'evidence':
            return evidence_dir()
        if self.root == 'repo':
            return REPO
        if self.root == 'snapshot':
            return snapshot_dir()
        raise ValueError(f'pin {self.name}: unknown root {self.root!r}')

    def default(self) -> Path | None:
        """The configured location: the first set environment variable, else the default location.
        None when neither exists (a snapshot without MU_SNAPSHOT_DIR)."""
        for name in self.env:
            value = os.environ.get(name)
            if value:
                return Path(value).expanduser()
        root = self.root_dir()
        if root is None or self.relative is None:
            return None
        return root / self.relative

    def default_str(self) -> str | None:
        """default() as a string (argparse defaults); None when nothing is configured."""
        path = self.default()
        return None if path is None else str(path)

    def hint(self) -> str:
        moves = list(self.env)
        if self.root == 'evidence':
            moves.append(EVIDENCE_ENV)
        elif self.root == 'snapshot':
            moves.append(SNAPSHOT_ENV)
        where = f' (default {self.root}/{self.relative})' if self.relative else ''
        return f'set {" or ".join(moves)} or pass the path explicitly{where}' if moves else \
            f'pass the path explicitly{where}'

    def path(self, given=None) -> Path:
        """The path to use: ``given`` when set, else default(). Raises PinMissing when neither is known.
        Does not check that the file exists (require() does)."""
        if given not in (None, ''):
            return Path(given).expanduser()
        path = self.default()
        if path is None:
            raise PinMissing(f'pinned input {self.name!r} ({self.what}) has no configured location: {self.hint()}')
        return path

    def require(self, given=None) -> Path:
        path = self.path(given)
        if not path.is_file():
            raise PinMissing(f'pinned input {self.name!r} ({self.what}) is missing: {path} does not exist; '
                             f'{self.hint()}')
        return path

    def available(self, given=None) -> bool:
        try:
            return self.require(given).is_file()
        except PinMissing:
            return False

    # ---- identity ----------------------------------------------------------------------------
    def matches(self, payload: bytes) -> bool:
        return (self.size is None or len(payload) == self.size) and sha256_bytes(payload) == self.sha256

    def read(self, given=None, *, exit: bool = False, mismatch: BaseException | None = None) -> bytes:
        """The pinned bytes (the whole file, or the region), verified.

        ``exit=True`` turns a PinError into SystemExit with the same message (for command-line mains).
        ``mismatch`` is raised instead of PinMismatch when the bytes differ: a caller that promised its own
        error (``ValueError('... pinned restored client text')``, tested elsewhere) keeps it."""
        try:
            path = self.require(given)
            payload = read_region(path, self.size, self.offset, self.whole)
            if not self.matches(payload):
                if mismatch is not None:
                    raise mismatch
                got = f'{len(payload)} bytes, SHA-256 {sha256_bytes(payload)}'
                raise PinMismatch(f'{path} does not match the pinned {self.name!r} ({self.what}): expected '
                                  f'{self.size} bytes, SHA-256 {self.sha256}; got {got}')
            return payload
        except PinError as error:
            if exit:
                raise SystemExit(str(error)) from None
            raise

    def describe(self) -> dict:
        path = self.default()
        return {'name': self.name, 'sha256': self.sha256, 'size': self.size, 'what': self.what,
                'default': None if path is None else str(path), 'env': list(self.env), 'root': self.root,
                'offset': self.offset, 'whole': self.whole, 'base': None if self.base is None else hex(self.base)}


def read_region(path, size, offset=0, whole=True) -> bytes:
    """A whole file (whole=True) or ``size`` bytes at ``offset``. PinMissing when the file is absent."""
    try:
        if whole and not offset:
            return Path(path).read_bytes()
        with open(path, 'rb') as handle:
            handle.seek(offset)
            return handle.read(size) if size is not None else handle.read()
    except FileNotFoundError:
        raise PinMissing(f'pinned input missing: {path} does not exist') from None


def load(path, size, digest, *, offset=0, whole=True, mismatch: BaseException | None = None) -> bytes:
    """Read and verify an input against an explicit (size, digest) pin: the shared body of the validators'
    old ``load_pinned``/``check_identity`` helpers and inline checks. ``size=None`` skips the size check.
    Raises PinMissing, or on a mismatch ``mismatch`` when given (the error a caller promised) and PinMismatch
    otherwise. Callers pass their own module constants, which tests may patch."""
    payload = read_region(path, size, offset, whole and not offset)
    if (size is not None and len(payload) != size) or sha256_bytes(payload) != digest:
        if mismatch is not None:
            raise mismatch
        raise PinMismatch(f'{path}: unexpected size or SHA-256')
    return payload


def loader(error=SystemExit, message='{label}: unexpected size or SHA-256 ({path})'):
    """A ``load_pinned(path, size, digest, label, offset=0)`` with a given failure contract.

    The validators carried about fifteen copies of this loader that differed only in the exception type and
    message they raise on a mismatch (callers and tests depend on those), so each keeps its contract and
    shares the body: the payload when it matches; PinMissing (a FileNotFoundError naming the path) when the
    file is absent; ``error(message)`` when it differs. ``offset`` reads a ``size``-byte region."""
    def load_pinned(path, size, digest, label, offset=0):
        try:
            return load(path, size, digest, offset=offset)
        except PinMismatch:
            raise error(message.format(label=label, path=path)) from None
    return load_pinned


# The contract of actor_machine and renderchar_machine (SystemExit naming the label and the path).
load_pinned = loader()


# =============================================================================================
# The registry. Sizes are whole-file sizes unless whole=False.

TEXT = Pin('text', '2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724', 23572480,
           'x86-text-capture-09/client-text.bin', env=('MU_CLIENT_TEXT',), base=0x00401000,
           what='restored client text section 0x00401000, x86 Linux Wine capture 09')
# The same bytes, captured earlier (capture 08); the client-memory and protocol checks default to it.
TEXT08 = Pin('text08', TEXT.sha256, TEXT.size, 'x86-capture-text-08/client-text.bin', env=('MU_CLIENT_TEXT',),
             base=0x00401000, what='restored client text section 0x00401000, x86 Linux Wine capture 08')
DATA = Pin('data', 'c985e2e6dcd155a4768081613c4bb4fa67172545bb250a1556a7f92e25a0672f', 2557764,
           'image-data-run10/data-capture-10/client-image-data.bin', env=('MU_IMAGE_DATA', 'MU_CLIENT_IMAGE_DATA'),
           base=0x01a7c000, what='second image section 0x01a7c000, run10 data capture 10')
FLAG = Pin('flag', '67abdd721024f0ff4e0b3f4c2fc13bc5bad42d0b7851d456d88d203d15aaa450', 4,
           'trig-state-15/captures/late/math-dispatch-flag.bin', env=('MU_TRIG_FLAG',), base=0x0bdd1cc8,
           what='trigonometric dispatch flag 0x0bdd1cc8, trig-state capture 15 (late)')
FEATURE = Pin('feature', 'bce941d196c26696f1f5d701d21a8a9e414e81d6e15a48f3663313e3cd7cc4b9', 4,
              'image-data-run10/math-capture-10/cpu-features.bin', env=('MU_CPU_FEATURES',), base=0x01cf6618,
              what='math CPU feature word 0x01cf6618, run10 math capture 10')
FEATURE09 = Pin('feature09', FEATURE.sha256, 4, 'x86-math-capture-09/cpu-features.bin', env=('MU_CPU_FEATURES',),
                base=0x01cf6618, what='math CPU feature word 0x01cf6618, x86 math capture 09')
RECORD_BIAS = Pin('record_bias', 'af5570f5a1810b7af78caf4bc70a660f0df51e42baf91d4de5b2328de0e83dfc', 8,
                  'image-data-run10/math-capture-10/record-bias.bin', base=0x01a7dd40,
                  what='record-math bias double 0x01a7dd40 (math capture)')
RECORD_TEMPLATE = Pin('record_template', '5998e9d1dd9bf48af6af87a1ef8c7783b818ac8329637ada08cc5fb329042376', 64,
                      'image-data-run10/math-capture-10/record-template.bin', base=0x01cf3b00,
                      what='record-math identity template 0x01cf3b00 (math capture)')
# The math-data capture directory (capture.json plus record-bias, record-template and cpu-features);
# record_math reads it whole. capture 09 is what its test defaults to; run10's math-capture-10 holds the
# same three files.
MATH_DATA_DIR = 'x86-math-capture-09'
MATH_DATA_ENV = 'MU_MATH_DATA'
# runtime-linux capture tool that wrote the math-data manifest (its capture_tool_sha256 field).
MATH_CAPTURE_TOOL_SHA256 = '11bcd31f1e502ad11c281fd048e4a6bb18fa922584edff33174c667bf4bf34d8'
SECTION3 = Pin('section3', '0571c519b1c4eaf97a143d2dd29bf2a3799e56b2f613cda0d084f4b857c1dc6f', 54525952,
               'x86-linux-capture-04/main-01ced000.bin', env=('MU_SECTION3', 'MU_DATA_SECTION'), base=0x01ced000,
               what='third section from 0x01ced000, x86-linux-capture-04 prefix file (not reproducible: the '
                    '2026-10-24 guest rebuild read a different whole-file digest)')
DIRECTIONS = Pin('directions', 'a8cc45492d67c784853284cd426fd5c48a994a55d124bd970c1da1e46616f8b5', 64,
                 'path-table-live-01/live-a-01ced000.bin', env=('MU_PATH_DIRECTIONS',), offset=0x01cf1640 - 0x01ced000,
                 whole=False, base=0x01cf1640,
                 what='path neighbour table 0x01cf1640 inside a third-section read (path-table-live-01, '
                      'x86-linux-capture-04 or x86-guest-sec3-25)')
TARGET = Pin('target', '3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a', 32229376,
             'input/main.exe', root='repo', env=('MU_TARGET_EXE',), what='the pinned client main.exe')
V14_MANIFEST = Pin('v14_manifest', 'fffcbad941e9bad394489382e79ad6d9d2e9f405847975de0eff113babd366ff', None,
                   'model-recovery/verified-v14/manifest.json', root='repo', env=('MU_V14_MANIFEST',),
                   what='verified-v14 private model corpus manifest')
EDGE_DIAGNOSTICS = Pin('edge_diagnostics', 'ba945b166c52e068a4ed12bbbc67a27f68d697fcf64197aaff627b09e45b909a', None,
                       'model-edge/diagnostics.json', env=('MU_EDGE_DIAGNOSTICS',),
                       what='rejected v15 model diagnostics (model-edge)')

# langread snapshots: local live-reader dumps recorded before the lane rules forbade live reads. They live
# outside the repository (MU_SNAPSHOT_DIR, e.g. a mu-mac-tools native/scratch folder); identities as in
# docs/research/client-maps.md.
# lang3's identity was not written down when it was read (2026-10-18, 5,656,246 bytes); VERIFY-HARNESS-001
# pinned the local copy, the one every lang3 result in docs/research came from.
LANG3 = Pin('lang3', 'f07b4c022e9cd1be2db8dd03052e9957254012bb8b893371eede749fecbf62a3', None,
            'lang/live/lang3.bin', root='snapshot', env=('MU_LANG3_SNAPSHOT',),
            what='langread snapshot lang3.bin (NATIVE-LANG-001 tables)')
LANG4 = Pin('lang4', '0461a408fd6b016def81043b43338d80d1851cec7bd7959ca8a2cf655dab9709', None,
            'lang/live/lang4.bin', root='snapshot', env=('MU_LANG4_SNAPSHOT',),
            what='langread snapshot lang4.bin (maps and quests)')
QUEST_LANG5 = Pin('quest_lang5', '2bd041e633122183514925fbbd0ae828972c358c728527ea1a9fc1752814b657', None,
                  'quest2/live/lang5.bin', root='snapshot', env=('MU_QUEST_LANG5_SNAPSHOT',),
                  what='langread snapshot quest2/live/lang5.bin (quest guide tables)')
SKILL_LANG5 = Pin('skill_lang5', '59974e2e44ef80fb4e3551000f691837bc8f7e411dab28436aaa6bf676f5adf5', None,
                  'skill2/live/lang5.bin', root='snapshot', env=('MU_SKILL_LANG5_SNAPSHOT',),
                  what='langread snapshot skill2/live/lang5.bin (nested skill maps)')

# NATIVE-SKILL-003's fourth-tree snapshot (docs/research/client-skills.md, scratch/skill3/live/s2_tree4.bin); the
# docs record no digest, VERIFY-HARNESS-001 pinned the local copy.
SKILL_TREE4 = Pin('skill_tree4', '65e69d1570292b600cea1ceb8908c10b5e9438cd71d8c75f15d424c7eac5d7d9', None,
                  'skill3/live/s2_tree4.bin', root='snapshot', env=('MU_SKILL_TREE4_SNAPSHOT',),
                  what='langread snapshot skill3/live/s2_tree4.bin (fourth skill tree tables)')
# NATIVE-LIGHT-001's login-scene inputs (docs/research/client-model-light.md: "Login, World95 (login-a)"): a
# lightread snapshot and the decoded object file of the same world; local copies pinned by VERIFY-HARNESS-001.
LIGHT_LOGIN = Pin('light_login', '140d09ee4181416820f1aae17c21048e44a7f0e21d9ab7a1e02cabf288a7ee4a', None,
                  'light/live/dumps/login-a.light', root='snapshot', env=('MU_LIGHT_SNAPSHOT',),
                  what='lightread snapshot login-a of the login scene (world 94)')
OBJECTS_LOGIN = Pin('objects_login', '8b94aba21bd18cb5d114f8918a7af8465d0fafe9a65576b0e885c7c2bb18716e', None,
                    'objects/live/plain/EncTerrain95.plain', root='snapshot', env=('MU_LIGHT_OBJECTS',),
                    what='decoded login-scene object file EncTerrain95 (local plaintext of an installed file)')

PINS = {pin.name: pin for pin in (TEXT, TEXT08, DATA, FLAG, FEATURE, FEATURE09, RECORD_BIAS, RECORD_TEMPLATE,
                                   SECTION3, DIRECTIONS, TARGET, V14_MANIFEST, EDGE_DIAGNOSTICS,
                                   LANG3, LANG4, QUEST_LANG5, SKILL_LANG5, SKILL_TREE4, LIGHT_LOGIN,
                                   OBJECTS_LOGIN)}
# Digests pinned here that are not files of their own (checked by tests/test_pins.py like the others).
OTHER_DIGESTS = {'math_capture_tool': MATH_CAPTURE_TOOL_SHA256}


def math_data_dir(given=None) -> Path:
    """The math-data capture directory: ``given``, else MU_MATH_DATA, else evidence/<MATH_DATA_DIR>."""
    if given not in (None, ''):
        return Path(given).expanduser()
    value = os.environ.get(MATH_DATA_ENV)
    return Path(value).expanduser() if value else evidence_dir() / MATH_DATA_DIR


def work_dir(name: str) -> Path:
    """A scratch directory for a validator's builds and temporary files: MU_VALIDATOR_WORK/<name> when set,
    else <system temporary directory>/<name> (the old hardcoded /tmp defaults). Created on demand."""
    import tempfile
    base = os.environ.get('MU_VALIDATOR_WORK')
    path = (Path(base).expanduser() if base else Path(tempfile.gettempdir())) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def digests() -> dict[str, str]:
    """Every digest this module pins, by name."""
    out = {name: pin.sha256 for name, pin in PINS.items()}
    out.update(OTHER_DIGESTS)
    return out


def main(argv=None) -> int:
    """`pins.py` lists every pin with its configured location and whether that file is present and
    matches (`--check`)."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('--check', action='store_true', help='read and verify every configured pin')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    rows = []
    for pin in PINS.values():
        row = pin.describe()
        if args.check:
            try:
                pin.read()
                row['status'] = 'ok'
            except PinMissing as error:
                row['status'], row['reason'] = 'missing', str(error)
            except PinMismatch as error:
                row['status'], row['reason'] = 'mismatch', str(error)
        rows.append(row)
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        for row in rows:
            print(f"{row['name']:16} {row['sha256'][:16]}… {row.get('status', ''):8} {row['default']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
