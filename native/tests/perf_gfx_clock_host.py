"""Probe AS2 getTimer through the real library with and without the test clock."""
import ctypes as c
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_gfx2 import assign_fn, conv, swf, tag
path, library = map(Path, sys.argv[1:])
code = assign_fn('_root', 'readTime', [], b'\x34\x3e')
path.write_bytes(swf([tag(69, bytes(4)), tag(12, code + b'\0'),
                      tag(12, conv.bridge_actions()), tag(1, b'')], version=9, size=(32, 32)))
d = c.CDLL(str(library))
d.mugfx_open.argtypes = [c.c_char_p, c.c_int, c.c_int, c.c_char_p, c.c_size_t]
d.mugfx_open.restype = c.c_void_p
for name in ('mugfx_start', 'mugfx_close'):
    getattr(d, name).argtypes = [c.c_void_p]
d.mugfx_advance.argtypes = [c.c_void_p, c.c_double]
d.mugfx_invoke.argtypes = [c.c_void_p, c.c_char_p, c.c_char_p, c.c_char_p]
d.mugfx_invoke.restype = c.c_char_p
error = c.create_string_buffer(1024)
g = d.mugfx_open(str(path).encode(), 32, 32, error, len(error))
assert g, error.value
try:
    d.mugfx_start(g)
    read = lambda: json.loads(d.mugfx_invoke(g, b'_root', b'readTime', b'[]'))
    first = read()
    time.sleep(.06)
    second = read()
    d.mugfx_advance(g, 40)
    third = read()
    print(json.dumps([first, second, third]))
finally:
    d.mugfx_close(g)
