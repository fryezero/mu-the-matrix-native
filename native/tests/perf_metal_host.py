"""Synthetic Metal timing probe, isolated so an FFI panic fails one child process."""
import ctypes as c
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_gfx2 import extension_movie
p=Path(sys.argv[1]);p.write_bytes(extension_movie())
d=c.CDLL(sys.argv[2]);d.mugfx_open_shared.argtypes=[c.c_char_p,c.c_int,c.c_int,c.c_char_p,c.c_size_t];d.mugfx_open_shared.restype=c.c_void_p
for name in ['mugfx_start','mugfx_close']:
 getattr(d,name).argtypes=[c.c_void_p]
d.mugfx_render_shared.argtypes=[c.c_void_p,c.c_int]
d.mugfx_advance.argtypes=[c.c_void_p,c.c_double]
d.mugfx_perf_frame.argtypes=[c.c_uint64]
err=c.create_string_buffer(1024);g=d.mugfx_open_shared(str(p).encode(),200,100,err,1024)
assert g,err.value
try:
 d.mugfx_start(g)
 for frame in range(3):
  d.mugfx_perf_frame(frame)
  if frame!=1:
   d.mugfx_advance(g,40)
   assert d.mugfx_render_shared(g,0)==0
  d.mugfx_perf_end()
finally:d.mugfx_close(g)
