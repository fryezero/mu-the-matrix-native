"""Recorded minimap routes, immutable session ownership and HUD refresh lifecycle."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from test_session_support import NATIVE as N, SCENARIOS, jnl, run_tool
ROOT=N.parent
FRAMEWORKS=['-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation'] if sys.platform=='darwin' else ['-ldl']
class Unit(C.Structure):
    _fields_=[('type',C.c_int32),('key',C.c_int32),('state',C.c_int32),('x',C.c_float),('y',C.c_float),('text',C.c_char*64)]
class MapOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.d=Path(cls.tmp.name)
        subprocess.run(['make','-C',str(N),'build/mu-session'],check=True,capture_output=True)
        cls.host=cls.d/'host'
        subprocess.run(['cc','-std=c11','-DMU_SESSION_SEED','-DMU_GFX_NO_GL','-I',str(N/'build/gen'),'-I',str(N/'session'),'-I',str(ROOT/'reconstructed/hud'),
            str(N/'tests/map_overlay_session_host.c'),str(N/'world/world_gfx_map.c'),str(N/'gfx/mu_gfx_layer.c'),
            str(N/'build/libmusession.a'),str(N/'build/libmunative.a'),*FRAMEWORKS,'-lm','-o',str(cls.host)],check=True,capture_output=True)
        cls.lib=cls.d/'parse.dylib'
        subprocess.run(['cc','-shared','-fPIC',str(N/'session/domains/map_overlay_wire.c'),str(ROOT/'reconstructed/map/map_hud.c'),'-o',str(cls.lib)],check=True,capture_output=True)
        cls.parse=C.CDLL(str(cls.lib));cls.parse.mu_map_overlay_detect_parse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(Unit)]
        cls.parse.mu_map_overlay_marker_parse.argtypes=[C.c_char_p,C.c_size_t,C.POINTER(Unit)]
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def test_scenario_routes_and_atomic_rejection(self):
        r,rows=run_tool('fixture',SCENARIOS/'map_overlay-markers.scn')
        self.assertEqual(r.returncode,0,r.stderr)
        frames=jnl(rows,'frame_in');self.assertEqual(len(frames),9)
        self.assertEqual([f['result'] for f in frames],['done']*4+['ignored']*2+['done']*3)
        self.assertTrue(all(f['apply'].startswith('map_overlay_') for f in frames))
    def test_session_detach_rebind_and_lease_audit(self):
        p=subprocess.run([str(self.host),str(SCENARIOS/'map_overlay-markers.scn')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        p=subprocess.run([str(self.host),str(SCENARIOS/'map_overlay-markers.scn'),'mutate'],capture_output=True,text=True)
        self.assertNotEqual(p.returncode,0);self.assertIn('replicated zone',p.stderr)
    def test_full_collection_update_remove_and_reuse(self):
        scenario=self.d/'capacity.scn'
        lines=['endpoint game 127.0.0.1:55907']
        for key in range(128):lines.append('at 1 send game c1 0a e7 04 %02x 00 00 00 01 01'%key)
        lines+=['at 2 send game c1 0a e7 04 c8 00 00 00 01 01',
                'at 3 send game c1 0a e7 04 01 00 00 00 fa 01',
                'at 4 send game c1 0a e7 04 00 00 00 01 00 00',
                'at 4 send game c1 0a e7 04 c8 00 00 00 01 01']
        scenario.write_text('\n'.join(lines)+'\n')
        r=subprocess.run([str(self.host),str(scenario),'capacity'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
    def test_malformed_heads_count_bounds_and_zero_kind(self):
        out=(Unit*256)()
        def packet(n,body):
            p=b'\xc2\0\0\xe7\x05\0\0'+struct.pack('<H',n)+body
            return p[:1]+len(p).to_bytes(2,'big')+p[3:]
        for n in [0,1,255,256]:
            p=packet(n,b'\x02\x34\x12\x78\x56'*n)
            self.assertEqual(self.parse.mu_map_overlay_detect_parse(p,len(p),out),n)
            if n:self.assertEqual((out[n-1].key,out[n-1].x),(n-1,0x1234*2))
        p=packet(257,b'\x01\0\0\0\0'*257)
        self.assertEqual(self.parse.mu_map_overlay_detect_parse(p,len(p),out),-1)
        p=packet(300,b'\0'*1500)
        self.assertEqual(self.parse.mu_map_overlay_detect_parse(p,len(p),out),0)
        for p in [packet(2,b'\x01\0\0\0\0'),packet(0,b'\0'),b'\xc1\x09\xe7\x05\0\0\0\0\0']:
            self.assertEqual(self.parse.mu_map_overlay_detect_parse(p,len(p),out),-1)
        u=Unit()
        for p in [b'\xc1\x0b\xe7\x03\x01\x01\0\0\0\0X',b'\xc2\0\x0b\xe7\x03'+b'\0'*6]:
            self.assertEqual(self.parse.mu_map_overlay_marker_parse(p,len(p),C.byref(u)),-1)
    def test_hud_refresh_and_host_rebind(self):
        lib=self.d/'stub.dylib'
        subprocess.run(['cc','-shared','-fPIC',str(N/'tests/gfx_stub_mugfx.c'),'-o',str(lib)],check=True,capture_output=True)
        movies=self.d/'movies';movies.mkdir(exist_ok=True)
        for name in ['base','main','chat']:(movies/(name+'.swf')).write_bytes(b'synthetic')
        log=self.d/'calls.log'
        r=subprocess.run([str(self.host),str(SCENARIOS/'map_overlay-markers.scn'),str(movies),str(lib),str(self.d),'stub'],env=dict(os.environ,MUGFX_STUB_LOG=str(log)),capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        calls=log.read_text()
        self.assertIn('Updated guide',calls);self.assertIn('AddDetectedUnit [[{"type":2,"key":0',calls)
        self.assertIn('AddDetectedUnit [[]]',calls)
        self.assertGreater(calls.count('"Updated guide"'),1)
        self.assertNotIn('Entrance',calls)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private pinned instructions')
class Private(unittest.TestCase):
    def test_recorded_map_handlers(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_session_map_overlay.py'),'--cases','40','--mutants','--output',str(out)],check=True,capture_output=True)
            r=json.loads(out.read_text())
        self.assertEqual((r['cases'],r['mismatches'],len(r['mutants_caught'])),(120,0,4))
