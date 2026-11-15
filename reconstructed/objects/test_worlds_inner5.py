"""Authored context guards, refusal and overflow behavior for INNER-005."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_worlds_inner5 as inner
import validate_object_render as v
class Helpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.lib=inner.build(ROOT/'reconstructed')
    def test_missing_context_refuses_before_writes_or_rng(self):
        for world,typ in [(24,15),(25,29),(36,32),(39,0)]:
            o=C.create_string_buffer(v.OBJ_SIZE);C.c_int32.from_buffer(o,0x5c).value=typ
            before=o.raw;log=v.new_log();rnd=v.RAND_FN(lambda c:self.fail('refused RNG'))
            if world==39:self.lib.dll.mu_tower_zero(o,0,world,None,rnd,inner.w2.BONE_FN(),None,C.byref(log))
            else:self.lib.dll.mu_kalima_helpers(o,0,world,0,None,inner.w3.NAMED_FN(),None,C.byref(log))
            self.assertEqual(o.raw,before);self.assertEqual([e[0] for e in v.log_events(log)],[0xdef747])
    def test_wrong_world_and_type(self):
        for world in range(-1,147):
            for typ in (0,12,15,29,32,35):
                o=C.create_string_buffer(v.OBJ_SIZE);C.c_int32.from_buffer(o,0x5c).value=typ
                l=v.new_log();f=inner.Kalima();t=inner.Tower();t.phase=-1
                ans=self.lib.dll.mu_kalima_helpers(o,0,world,0,C.byref(f),inner.w3.NAMED_FN(),None,C.byref(l))
                self.assertEqual(ans,int(world in (*range(24,30),36) and typ in (15,29,32)))
                ans=self.lib.dll.mu_tower_zero(o,0,world,C.byref(t),v.RAND_FN(lambda c:0),inner.w2.BONE_FN(),None,C.byref(l))
                self.assertEqual(ans,int(world==39 and typ==0))
    def test_overflow_keeps_sequence_state_and_full_rng(self):
        seeds=[]
        for capacity in (1,4096):
            o=C.create_string_buffer(v.OBJ_SIZE);f=inner.Tower();f.phase=0;r=v.MsvcRand(1);l=v.new_log(capacity)
            self.lib.dll.mu_tower_zero(o,0,39,C.byref(f),v.RAND_FN(lambda c:r()),inner.w2.BONE_FN(),None,C.byref(l))
            self.assertEqual(f.phase,-1);self.assertEqual(l.overflow,int(capacity==1));seeds.append(r.seed)
        self.assertEqual(*seeds)
@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private original text/data required')
class ClientComparison(unittest.TestCase):
    def test_registry_registration_callers(self):
        import re
        import struct
        import actor_machine as am
        import world_handler_coverage as wh
        text=am.load_pinned(v.pins.TEXT.default_str(),am.TEXT_BYTES,am.TEXT_SHA256,'text')
        data=am.load_pinned(v.pins.DATA.default_str(),am.DATA_BYTES,am.DATA_SHA256,'data')
        rows=wh.inventory(text,data)
        self.assertFalse(any(w in row['worlds'] for row in rows for w in (46,98)))
        for target,count in [(0xea8cf9,57),(0xea4452,48)]:
            refs=[m.start()+am.TEXT_BASE for m in re.finditer(b'\\xe8',text)
                  if m.start()+5<=len(text) and m.start()+am.TEXT_BASE+5+struct.unpack_from('<i',text,m.start()+1)[0]==target]
            self.assertEqual(len(refs),count)
            self.assertTrue(all(0xea488e<=a<0xea5629 for a in refs))
    def test_original(self):
        subprocess.run([sys.executable,str(ROOT/'scripts/validate_worlds_inner5.py'),'--cases','200'],check=True,capture_output=True)
if __name__=='__main__':unittest.main()
