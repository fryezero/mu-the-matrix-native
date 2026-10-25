"""Shared helpers for the session tests (no tests here): run build/mu-session, parse its JSON rows, undo XorData."""
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
TOOL = NATIVE / 'build/mu-session'
SCENARIOS = NATIVE / 'fixture/scenarios'

# the client's 32-byte send key (XorData immediates at 0x00d5205e), as test_protocol.py states it
KEY = bytes([0xab, 0x11, 0xcd, 0xfe, 0x18, 0x23, 0xc5, 0xa3, 0xca, 0x33, 0xc1, 0xcc, 0x66, 0x67, 0x21, 0xf3,
             0x32, 0x12, 0x15, 0x35, 0x29, 0xff, 0xfe, 0x1d, 0x44, 0xef, 0xcd, 0x41, 0x26, 0x3c, 0x4e, 0x4d])


def run_tool(*args, env=None, timeout=120):
    r = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True, env=env, timeout=timeout)
    rows = [json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
    return r, rows


def first(rows, key):
    """The first summary row of that name (an object; client rows carry a string "status")."""
    return next(r[key] for r in rows if isinstance(r.get(key), dict))


def jnl(rows, kind):
    return [r for r in rows if r.get('jnl') == kind]


def unxor(wire: bytes, header_len: int) -> bytes:
    """Undo the client's XorData over every byte after the opcode (the C1 request builders)."""
    obj = bytearray([len(wire) & 0xff, len(wire) >> 8]) + bytearray(wire)
    for i in range(len(wire) - 1, header_len, -1):
        obj[i + 2] ^= obj[i + 1] ^ KEY[i & 31]
    return bytes(obj[2:])


def hexbytes(text: str) -> bytes:
    return bytes(int(x, 16) for x in text.split())


def write_scenario(path: Path, text: str) -> Path:
    path.write_text(text)
    return path
