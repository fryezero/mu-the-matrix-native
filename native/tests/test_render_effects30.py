"""Demo skill caller admission, pixels, retirement and explicit consumer refusals."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'native/tests'))
from test_native_combat import write_combat_world
import native_fixtures as nf
from test_native_particles import ozj_jpeg
class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/mu-walk'],check=True,capture_output=True)
        cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'mu-walk'
        shutil.copy2(ROOT/'native/build/mu-walk',cls.binary)
        cls.root=Path(write_combat_world(Path(cls.tmp.name)/'game'))
        skill=cls.root/'Data/Skill';skill.mkdir(exist_ok=True)
        (skill/'Arrow01.bmd').write_bytes(nf.synthetic_layout(400,actions=1,keys=(8,)))
        effect=cls.root/'Data/Effect';effect.mkdir(exist_ok=True)
        (effect/'smoke01.OZJ').write_bytes(ozj_jpeg(32,32))
        cls.placement=Path(cls.tmp.name)/'actors.txt';cls.placement.write_text('actor 3 120 123 0 label DemoOther\nactor 3 122 120 0 label DemoTarget\n')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def cast(self,skill,cls=2,weapon='bow',frames=90):
        with tempfile.TemporaryDirectory() as tmp:
            p=subprocess.run([str(self.binary),'--game-root',str(self.root),'--headless','--backend','soft',
                '--no-audio','--no-items','--no-players','--tile','120,120','--placement',str(self.placement),
                '--combat','--class',str(cls),'--combat-weapon',weapon,'--combat-script',
                f'2:skill:{skill}:DemoTarget;3:stop','--frames',str(frames),'--every','1','--width','240',
                '--height','160','--out-dir',tmp],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr[-2000:])
            rows=[json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
            images=[hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(Path(tmp).glob('*.png'))]
        return rows,images
    def test_ice_arrow_draws_repeats_and_retires_for_base_and_promoted_elf(self):
        for cls in [2,0x12]:
            rows,on=self.cast(51,cls)
            summary=next(r for r in rows if r.get('combat') is True)
            self.assertEqual((summary['requests_sent'],summary['requests_unsent'],summary['hits'],summary['kills']),(0,1,0,0))
            plan=next(r for r in rows if r.get('skill30'))
            self.assertEqual((plan['arrow_calls'],plan['refused']),(1,0))
            self.assertGreater(plan['target_slot'],0)
            self.assertEqual(plan['target_index'],plan['target_slot'])
            self.assertNotEqual(plan['target_index'],plan['target_key'])
            frames=[r for r in rows if 'combat_frame' in r]
            self.assertTrue(any(r['fx'] for r in frames))
            self.assertEqual(frames[-1]['fx'],0)
            self.assertTrue(all(r['monsters'][0]['hp']==frames[0]['monsters'][0]['hp'] for r in frames))
            _,repeat=self.cast(51,cls);self.assertEqual(on,repeat)
            arrow=self.root/'Data/Skill/Arrow01.bmd';hidden=arrow.with_suffix('.off')
            arrow.rename(hidden)
            try:_,off=self.cast(51,cls)
            finally:hidden.rename(arrow)
            self.assertNotEqual(on,off)
    def test_missing_consumers_are_counted_and_never_change_target_hp(self):
        for skill,cls,weapon,refused in [(52,2,'bow',2),(48,1,'sword',38),(344,1,'sword',1)]:
            rows,_=self.cast(skill,cls,weapon)
            plan=next(r for r in rows if r.get('skill30'))
            self.assertEqual(plan['refused'],refused,(skill,plan))
            frames=[r for r in rows if 'combat_frame' in r]
            self.assertTrue(all(r['monsters'][0]['hp']==frames[0]['monsters'][0]['hp'] for r in frames))
    def test_wrong_class_weapon_and_stale_skill_have_no_new_visuals(self):
        for skill,cls,weapon in [(51,1,'bow'),(52,2,'sword'),(48,2,'bow'),(344,2,'bow'),(47,1,'sword')]:
            rows,_=self.cast(skill,cls,weapon,6)
            self.assertFalse(any(r.get('skill30') for r in rows))
    def test_triple_shot_preserves_both_original_requests_and_master_selectors(self):
        for skill,calls in [(24,2),(416,1),(424,1)]:
            rows,_=self.cast(skill,0x12)
            plan=next(r for r in rows if r.get('skill30'))
            self.assertEqual(plan['arrow_calls'],calls)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class Original(unittest.TestCase):
    def test_original_caller_streams(self):
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/combat')],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_effects30.py'),'--cases','70',
                '--output',str(output)],check=True,cwd=ROOT,capture_output=True)
            report=json.loads(output.read_text())
        self.assertTrue(report['all_equal']);self.assertEqual(report['cases'],452)

    def test_original_alias_brand_walks(self):
        # The real 0x00bb1c32 walks authored lookup records. No base-result stub.
        import ctypes as C
        import struct
        sys.path.insert(0,str(ROOT/'scripts'))
        import actor_machine as am
        import pins
        import validate_combat as vc
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/combat')],check=True,capture_output=True)
        lib=C.CDLL(str(ROOT/'reconstructed/combat/libcombat.dylib'))
        lib.mu_skill30_select.argtypes=[C.c_int32,C.c_int32]
        machine=vc.Combat(pins.TEXT.read(),pins.DATA.read())
        for skill,expected in [(416,52),(424,51)]:
            for supplied in [expected,51 if expected==52 else 52,0]:
                address=0x2a000000
                alias=am.undefined_region('alias',address,0xd0)
                alias.define(address+4,struct.pack('<i',skill))
                alias.define(address+0x5c,struct.pack('<i',supplied))
                base=am.undefined_region('base',address+0x1000,0xd0)
                base.define(address+0x1004,struct.pack('<i',supplied))
                base.define(address+0x105c,bytes(4))
                def lookup(mm):
                    return (address if mm.argument(0)==skill else address+0x1000,4)
                result=machine.execute(0xbb1c32,[skill],[alias,base],{0x961620:lookup},ecx=0x1234,cleanup=4)
                with self.subTest(skill=skill,supplied=supplied):
                    self.assertTrue(vc.ok(result),result)
                    selected=result['eax']
                    self.assertEqual(selected,supplied or skill)
                    self.assertEqual(bool(lib.mu_skill30_select(skill,selected)),supplied==expected)
