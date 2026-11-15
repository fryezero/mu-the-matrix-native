"""Fixture-only remaining learned skill requests and equipment action context."""
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
        subprocess.run(['make','-s','-j2','-C',str(ROOT/'native'),'build/mu-walk'],check=True,capture_output=True)
        cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'mu-walk'
        shutil.copy2(ROOT/'native/build/mu-walk',cls.binary)
        cls.root=Path(write_combat_world(Path(cls.tmp.name)/'game'))
        effect=cls.root/'Data/Effect';effect.mkdir(exist_ok=True)
        (effect/'smoke01.OZJ').write_bytes(ozj_jpeg(32,32))
        skill=cls.root/'Data/Skill';skill.mkdir(exist_ok=True)
        (skill/'Arrow01.bmd').write_bytes(nf.synthetic_layout(400,actions=1,keys=(8,)))
        cls.placement=Path(cls.tmp.name)/'actors.txt';cls.placement.write_text('actor 3 122 120 0 label DemoTarget\n')
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def cast(self,skill,cls=1,weapon='sword',context=None,frames=50,bow_item=None):
        env=dict(os.environ);env.pop('MU_SKILL32_CONTEXT',None)
        if context is not None:env['MU_SKILL32_CONTEXT']=context
        with tempfile.TemporaryDirectory() as tmp:
            args=[str(self.binary),'--game-root',str(self.root),'--headless','--backend','soft',
                '--no-audio','--no-items','--no-players','--tile','120,120','--placement',str(self.placement),
                '--combat','--class',str(cls),'--combat-weapon',weapon,'--combat-script',
                f'2:skill:{skill}:DemoTarget;3:stop','--frames',str(frames),'--every','1','--width','240',
                '--height','160','--out-dir',tmp]
            if bow_item is not None:args.extend(['--combat-bow',str(bow_item)])
            p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr[-2000:])
            rows=[json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
        return rows
    def assert_safe(self,rows):
        summary=next(r for r in rows if r.get('combat') is True)
        self.assertEqual((summary['requests_sent'],summary['requests_unsent'],summary['hits'],summary['kills']),(0,1,0,0))
        frames=[r for r in rows if 'combat_frame' in r]
        self.assertTrue(all(r['monsters'][0]['hp']==frames[0]['monsters'][0]['hp'] for r in frames))
        return frames
    def test_seven_summons_keep_missing_actor_explicit(self):
        for skill in range(30,37):
            rows=self.cast(skill,2,'bow');self.assert_safe(rows)
            plan=next(r for r in rows if r.get('skill32'))
            self.assertEqual((plan['casts'],plan['requests'],plan['refused']),(1,1,0))
    def test_shield_pose_requires_authored_context(self):
        self.assertFalse(any(r.get('skill32') for r in self.cast(18)))
        rows=self.cast(18,context='0,-1,1,0');frames=self.assert_safe(rows)
        self.assertTrue(any(r['hero_action']==0xd7 for r in frames),frames)
        plan=next(r for r in rows if r.get('skill32'))
        self.assertEqual((plan['requests'],plan['refused']),(0,0))
    def test_mount_pose_keeps_fire_consumer_refused(self):
        self.assertFalse(any(r.get('skill32') for r in self.cast(49)))
        rows=self.cast(49,context='0,-1,0,1');frames=self.assert_safe(rows)
        self.assertTrue(any(r['hero_action']==0xf9 for r in frames))
        plan=next(r for r in rows if r.get('skill32'))
        self.assertEqual((plan['requests'],plan['refused']),(1,1))
    def test_crescent_requests_existing_sparks_and_missing_end_effect(self):
        rows=self.cast(44);frames=self.assert_safe(rows)
        self.assertTrue(any(r['hero_action']==0x98 for r in frames))
        plan=next(r for r in rows if r.get('skill32'))
        self.assertGreater(plan['requests'],8);self.assertEqual(plan['requests']%8,1)
        self.assertEqual(plan['refused'],1)
        self.assertTrue(any(r['particles'] or r['joints'] for r in frames))
        self.assertEqual((frames[-1]['particles'],frames[-1]['joints']),(0,0))
    def test_arrow_context_uses_wing_word_and_kind(self):
        for skill,weapon,kind,action in [(24,'bow',1,0x80),(51,'crossbow',2,0x81),(52,'bow',1,0x95),(416,'crossbow',2,0x96)]:
            rows=self.cast(skill,2,weapon,f'{kind},0,0,0');frames=self.assert_safe(rows)
            self.assertTrue(any(r['hero_action']==action for r in frames),(skill,frames))
    def test_invalid_context_does_not_enable_special_poses(self):
        for context in ['0,-1,1,0x', '0,-1,2,1', '3,-1,1,1', '0,-2,1,1']:
            self.assertFalse(any(r.get('skill32') for r in self.cast(18,context=context,frames=6)))

    def test_default_step_exceptional_item_is_outside_fixture_admission(self):
        for skill,cls,context in [(30,2,None),(18,1,'1,-1,1,0')]:
            self.assertFalse(any(r.get('skill32') for r in
                self.cast(skill,cls,'bow',context,frames=6,bow_item=0x12fb)))
            self.assertTrue(any(r.get('skill32') for r in
                self.cast(skill,cls,'bow',context,frames=6,bow_item=0x12fa)))

    def test_wrong_class_stale_and_unlearned_ids_remain_refused(self):
        for skill,cls in [(47,1),(432,2),(30,1),(44,2),(18,2),(49,2)]:
            self.assertFalse(any(r.get('skill32') for r in self.cast(skill,cls,context='1,-1,1,1',frames=6)))

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class Original(unittest.TestCase):
    def test_original_remaining_callers(self):
        subprocess.run(['make','-s','-j2','-C',str(ROOT/'reconstructed/combat')],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_effects32.py'),'--cases','100',
                '--output',str(output)],check=True,cwd=ROOT,capture_output=True)
            report=json.loads(output.read_text())
        self.assertTrue(report['all_equal'])
