"""Guard, authored-input, overflow and original-instruction tests for INNER-004."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_worlds_inner4 as inner
import validate_object_render as v
class Inline4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.lib=inner.build(ROOT/'reconstructed')
    def call(self,world,typ,event=0,model=1,capacity=64):
        o=C.create_string_buffer(v.OBJ_SIZE);C.c_int32.from_buffer(o,0x5c).value=typ
        C.c_int32.from_buffer(o,0x68).value=-1;C.c_float.from_buffer(o,0xa0).value=2
        log=v.new_log(capacity);r=v.RAND_FN(lambda c:0)
        if world==30:answer=self.lib.dll.mu_crywolf_inner(o,0,world,model,0,event,r,None,C.byref(log))
        else:answer=self.lib.dll.mu_barracks_inner(o,0,world,model,0,r,None,C.byref(log))
        return answer,o,log
    def test_guard_and_model(self):
        for world in range(-1,146):
            answer,o,l=self.call(world,6)
            self.assertEqual(answer,int(world in (30,41,42)))
        for world in (30,41,42):
            answer,o,l=self.call(world,6,model=0)
            self.assertEqual((answer,l.count),(0,0))
    def test_authored_event_byte(self):
        for event in (0,1,2,255):
            for typ in (0,0x2a,0x34,0x35,0x36):
                _,o,l=self.call(30,typ,event)
                want=int((event==0) if typ in (0,0x34,0x36) else event!=0)
                self.assertEqual(l.count,want,(event,typ))
    def test_smoke_and_log_overflow_keep_hidden_write(self):
        for world in (41,42):
            _,o,l=self.call(world,6,capacity=1)
            self.assertEqual((l.count,l.overflow),(1,1))
            self.assertEqual(C.c_int32.from_buffer(o,0x68).value,-2)
    def test_context_refusals_preserve_input(self):
        for world,typ in [(24,15),(25,29),(36,32),(39,0)]:
            o=C.create_string_buffer(v.OBJ_SIZE);C.c_int32.from_buffer(o,0x5c).value=typ
            before=o.raw;log=v.new_log();rnd=v.RAND_FN(lambda c:self.fail('refusal must not consume RNG'))
            if world==39:self.lib.dll.mu_tower_inner(o,0,world,0,0,rnd,inner.w2.BONE_FN(),None,C.byref(log))
            else:self.lib.dll.mu_kalima_inner(o,0,world,0,rnd,inner.w3.NAMED_FN(),None,C.byref(log))
            self.assertEqual(o.raw,before)
            self.assertEqual([e[0] for e in v.log_events(log)],[0xdef747])

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private original text/data required')
class ClientComparison(unittest.TestCase):
    def test_unregistered_worlds(self):
        import actor_machine as am
        import world_handler_coverage as wh
        rows=wh.inventory(am.load_pinned(v.pins.TEXT.default_str(),am.TEXT_BYTES,am.TEXT_SHA256,'text'),
                          am.load_pinned(v.pins.DATA.default_str(),am.DATA_BYTES,am.DATA_SHA256,'data'))
        self.assertEqual(len(rows),48)
        self.assertEqual(sum(len(row['worlds']) for row in rows),57)
        self.assertFalse(any(w in row['worlds'] for row in rows for w in (46,98)))
    def test_original(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_worlds_inner4.py'),'--cases','200'],check=True,capture_output=True)
if __name__=='__main__':unittest.main()
