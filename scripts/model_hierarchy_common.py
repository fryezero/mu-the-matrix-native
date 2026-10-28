#!/usr/bin/env python3
"""Pinned-input helpers for the MODEL-HIERARCHY-001 instruction study.

Only the verified restored first section and second image section are accepted.
Nothing here executes client code; it decodes bytes with Capstone and reports
what the decoded instructions literally do.
"""
import errno
import hashlib
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pins  # noqa: E402

TARGET_SHA256 = pins.TARGET.sha256
TEXT_BASE = pins.TEXT.base
TEXT_BYTES = pins.TEXT.size
TEXT_SHA256 = pins.TEXT.sha256
DATA_BASE = pins.DATA.base
DATA_BYTES = pins.DATA.size
DATA_SHA256 = pins.DATA.sha256


class PinError(ValueError):
    pass


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_pinned(path, size, digest):
    try:
        return pins.load(path, size, digest)
    except pins.PinMissing:
        # Callers also depend on the native missing-file message and exception fields.
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(Path(path))) from None
    except pins.PinMismatch:
        # Only rejected inputs need another read for this tool's detailed legacy diagnostics.
        data = Path(path).read_bytes()
        if len(data) != size:
            raise PinError(f'{path}: expected {size} bytes, found {len(data)}') from None
        found = sha256(data)
        raise PinError(f'{path}: SHA-256 {found} does not match pinned {digest}') from None


def load_text(path):
    return Region(TEXT_BASE, load_pinned(path, TEXT_BYTES, TEXT_SHA256))


def load_data(path):
    return Region(DATA_BASE, load_pinned(path, DATA_BYTES, DATA_SHA256))


class Region:
    """Bytes mapped at a virtual address; reads outside the region fail."""

    def __init__(self, base, data):
        if base < 0 or base + len(data) > 2**32:
            raise ValueError('region must fit in a 32-bit address space')
        self.base = base
        self.data = bytes(data)

    @property
    def end(self):
        return self.base + len(self.data)

    def contains(self, va, size=1):
        return self.base <= va and va + size <= self.end

    def read(self, va, size):
        if size < 0 or not self.contains(va, size):
            raise ValueError(f'{va:#x}+{size} lies outside {self.base:#x}..{self.end:#x}')
        offset = va - self.base
        return self.data[offset:offset + size]


def decoder():
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    engine = Cs(CS_ARCH_X86, CS_MODE_32)
    engine.detail = True
    return engine


def decode_range(region, start, end, engine=None):
    """Linear decode from a caller-asserted instruction boundary.

    Returns (instructions, stop) where stop is None when decoding reached `end`
    exactly, or the first address Capstone could not decode.  Landing past
    `end` is reported as a boundary error rather than silently truncated.
    """
    if not start < end or not region.contains(start, end - start):
        raise ValueError('decode range must be nonempty and inside the region')
    engine = engine or decoder()
    # Read up to one maximum-length instruction past `end` so an instruction
    # straddling the boundary is decoded and reported as an overrun.
    code = region.read(start, min(end + 15, region.end) - start)
    out, cursor = [], start
    for instruction in engine.disasm(code, start):
        if instruction.address != cursor or cursor >= end:
            break
        out.append(instruction)
        cursor = instruction.address + instruction.size
    if cursor == end:
        return out, None
    if cursor > end:
        raise ValueError(f'decode overran end {end:#x} at {out[-1].address:#x}; '
                         f'{start:#x} is not aligned with it')
    return out, cursor


def text_of(instruction):
    return f'{instruction.mnemonic} {instruction.op_str}'.strip()
