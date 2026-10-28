"""Public lifecycle, bounded logging and private instruction comparisons."""
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
import validate_worlds_j as j
class WorldsJTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/objects')],check=True)
        cls.lib=j.bind(v.Library(ROOT/f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll
    def create(self,world,typ):
        record=v.Record();record.type=typ;record.position[:]=[100,200,300];record.scale=2
        out=C.create_string_buffer(v.OBJ_SIZE);sector=C.c_int32();log=v.new_log()
        self.assertEqual(self.lib.mu_obj_create(C.byref(record),world,out,C.byref(sector),0,C.byref(log)),0)
        return out
    def test_public_move_hides_emitters_and_ticks_once(self):
        rnd=v.RAND_FN(lambda ctx:0);speed=v.SPEED_FN(lambda ctx,t,a:0)
        for world in (80,81):
            for typ in (113,114,115,116,118,135):
                obj=self.create(world,typ);inputs=v.MoveInputs()
                inputs.world=world;inputs.has_model=1;inputs.scene_state=6;inputs.rand_fn=rnd;inputs.speed=speed
                log=v.new_log();self.lib.mu_obj_move(obj,0,C.byref(inputs),C.byref(log))
                self.assertEqual(struct.unpack_from('<i',obj.raw,0x68)[0],-2)
                events=v.log_events(log)
                self.assertEqual(sum(e[0]==0x12b4dd3 for e in events),1)
                if typ==113:self.assertIn((0x16cacfc,0,v.bits(100),v.bits(200),v.bits(0.3),v.bits(v.f32(0.3)*v.f32(0.6)),v.bits(v.f32(0.3)*v.f32(0.2)),3),events)
                if typ==135:self.assertIn((0xa6ac96,0,0x5a5,0,0),events)
        self.assertEqual(self.lib.mu_karutan_create(None),0)
    def test_log_capacity_preserves_state_rng_and_bone_order(self):
        for world,typ in [(57,70),(58,80)]+[(80,t) for t in (66,72,113,114,115,116,118)]:
            results=[]
            for capacity in (0,1,64):
                obj=self.create(world,typ);struct.pack_into('<i',obj,0x68,-1)
                log=v.new_log(capacity);rng=v.MsvcRand(1);rnd=v.RAND_FN(lambda ctx:rng());bones=[]
                def bone(ctx,k,local,out):
                    bones.append((k,tuple(local[:3])))
                    for q in range(3):out[q]=local[q]+k
                cb=j.BONE(bone)
                if world==80:self.lib.mu_karutan_visual(obj,0,world,1000,rnd,cb,None,C.byref(log))
                else:self.lib.mu_raklion_visual(obj,0,1,rnd,None,C.byref(log))
                results.append((obj.raw,rng.seed,bones));self.assertLessEqual(log.count,capacity)
            self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-j-test-') as td:
            report=Path(td)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_worlds_j.py'),'--cases','1000','--mutations','--output',str(report)],check=True,capture_output=True)
            result=json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()),6000)
            self.assertTrue(all(r['cases']==r['equal'] and r['stopped']==0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']),30)
            self.assertTrue(all(m['detected']>0 and m['stopped']==0 for m in result['mutants']))
