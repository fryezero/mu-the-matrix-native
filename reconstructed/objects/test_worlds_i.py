"""Public lifecycle dispatch, bounded logs and private original instructions."""
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
import validate_object_render as v
import validate_worlds_i as i

class WorldsITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/objects')],check=True)
        cls.lib=i.bind(v.Library(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

    def create(self,world,typ):
        record=v.Record();record.type=typ;record.position[:]=[100,200,300];record.scale=2
        out=C.create_string_buffer(v.OBJ_SIZE);sector=C.c_int32();log=v.new_log()
        self.assertEqual(self.lib.mu_obj_create(C.byref(record),world,out,C.byref(sector),0,C.byref(log)),0)
        return out,log

    def test_public_dispatch_and_original_extra_alpha_step(self):
        obj,log=self.create(79,67)
        self.assertIn((0x16d9f51,0,1),v.log_events(log))
        self.assertEqual(struct.unpack_from('<3f',obj.raw,0x134),(100,100,160))
        obj,_=self.create(100,20)
        self.assertEqual(struct.unpack_from('<f',obj.raw,0xc0)[0],-400)
        rand=v.RAND_FN(lambda ctx:0);speed=v.SPEED_FN(lambda ctx,t,a:0)
        for world,typ in [(79,8),(100,44)]:
            obj,_=self.create(world,typ)
            struct.pack_into('<fff',obj,0xd8,0,1,0.5)
            inputs=v.MoveInputs();inputs.world=world;inputs.has_model=1;inputs.scene_state=6
            inputs.rand_fn=rand;inputs.speed=speed;log=v.new_log()
            self.assertEqual(self.lib.mu_obj_move(obj,0,C.byref(inputs),C.byref(log)),0)
            self.assertEqual(struct.unpack_from('<f',obj.raw,0xdc)[0],0.25 if world==79 else 0.5)
            self.assertEqual(sum(e[0]==0x12b4dd3 for e in v.log_events(log)),1)
            if world==79:self.assertAlmostEqual(struct.unpack_from('<f',obj.raw,0xbc)[0],0.2)
            else:self.assertAlmostEqual(struct.unpack_from('<f',obj.raw,0xb0)[0],-0.0035)

    def test_full_logs_do_not_change_state_or_rng(self):
        bone=i.BONE(lambda ctx,k,local,out:None)
        for world,typ in [(79,30),(79,54),(79,56),(79,57),(100,89),(100,92),(100,106),(100,108),(100,109)]:
            results=[]
            for capacity in (0,1,64):
                obj,_=self.create(world,typ);log=v.new_log(capacity);rng=v.MsvcRand(1);rnd=v.RAND_FN(lambda ctx:rng())
                if world==79:self.lib.mu_market_visual(obj,0,world,0,rnd,bone,None,C.byref(log))
                else:self.lib.mu_uruk_visual(obj,0,world,1,0,rnd,None,C.byref(log))
                results.append((obj.raw,rng.seed));self.assertLessEqual(log.count,capacity)
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-i-test-') as td:
            report=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_worlds_i.py'),'--cases','1000','--mutations','--output',str(report)],check=True,capture_output=True)
            result=json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()),6000)
            self.assertTrue(all(r['cases']==r['equal'] and r['stopped']==0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']),33)
            self.assertTrue(all(m['detected']>0 and m['stopped']==0 for m in result['mutants']))
            subprocess.run([sys.executable,str(ROOT/'scripts/world_handler_coverage.py')],check=True)
