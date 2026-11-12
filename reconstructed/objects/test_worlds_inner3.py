"""Aida guard, draw-state and bounded log checks, plus private original instruction comparison."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_worlds_inner3 as inner
import validate_object_render as v

class AidaInline(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.lib = inner.build(ROOT / 'reconstructed')

    def call(self, world, typ, clock=0, capacity=64):
        obj = C.create_string_buffer(v.OBJ_SIZE); C.c_int32.from_buffer(obj, 0x5c).value = typ
        C.c_int32.from_buffer(obj, 0x68).value = -1
        model = C.create_string_buffer(0x100); model[0x94] = b'\x03'
        log = v.new_log(capacity); rnd = v.RAND_FN(lambda c: 1)
        answer = self.lib.dll.mu_aida_inner(obj, model, 0, world, 0, clock, rnd,
                                          inner.w3.NAMED_FN(), None, C.byref(log))
        return answer, obj, model, log

    def test_world_and_clock_boundaries(self):
        for world in range(-1,146):
            for clock in (0,9,10,1023,1024,1033,1034,0xffffffff):
                answer,o,b,log = self.call(world,0x3c,clock)
                owned = world in (33,54)
                self.assertEqual(answer, int(owned))
                self.assertEqual(C.c_int32.from_buffer(o,0x68).value, -2 if owned else -1)
                self.assertEqual(log.count, int(owned and clock % 1024 < 10))

    def test_scroll_restores_model_even_on_overflow(self):
        for typ in (0x41,0x42,0x4d,0x4e):
            _,o,b,log = self.call(33,typ,capacity=1)
            self.assertEqual(b[0x94], b'\xff')
            self.assertEqual((log.count,log.overflow),(1,1))

    def test_twenty_owned_smoke_requests(self):
        _,o,b,log = self.call(33,0x3b)
        events=v.log_events(log)
        self.assertEqual(len(events),20)
        self.assertTrue(all(e[0]==inner.PARTICLE and e[-1]==1 for e in events))
        self.assertEqual(C.c_int32.from_buffer(o,0x68).value,-1)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private original text/data required')
class ClientComparison(unittest.TestCase):
    def test_original(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_worlds_inner3.py'),'--cases','200'],
                       check=True,capture_output=True)

if __name__ == '__main__': unittest.main()
