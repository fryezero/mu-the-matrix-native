"""Bounded producer logs and private original-instruction comparison."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_worlds_k as k
import validate_object_render as v
class WorldsKTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/objects')],check=True)
        cls.lib=k.bind(C.CDLL(str(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}')))
    def test_log_capacity_preserves_state_rng_and_one_shot_guard(self):
        for world,typ in [(4,19),(4,40),(8,60),(8,70),(8,83),(10,10)]:
            results=[]
            for capacity in [0,1,64]:
                obj=C.create_string_buffer(v.OBJ_SIZE);struct.pack_into('<i',obj,0x5c,typ);struct.pack_into('<f',obj,0xa0,1)
                rng=v.MsvcRand(1);rand=v.RAND_FN(lambda c:rng());bone=k.BONE(lambda c,n,i,o:None);log=v.new_log(capacity)
                self.lib.mu_builtin_visual(obj,0,world,1,3700,rand,bone,None,C.byref(log));self.assertLessEqual(log.count,capacity)
                results.append((obj.raw,rng.seed))
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-k-test-') as td:
            report=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_worlds_k.py'),'--cases','1200','--mutations','--output',str(report)],check=True,capture_output=True)
            r=json.loads(report.read_text());self.assertEqual(sum(x['cases'] for x in r['families'].values()),6000)
            self.assertTrue(all(x['equal']==x['cases'] and not x['stopped'] for x in r['families'].values()))
            self.assertEqual(len(r['mutants']),21);self.assertTrue(all(x['detected'] and not x['stopped'] for x in r['mutants']))
