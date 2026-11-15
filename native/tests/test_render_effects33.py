"""Learned-skill consumers and explicit optional target presentation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'native/tests'))
import test_render_effects32 as previous
import native_fixtures as nf
from test_native_particles import ozj_jpeg

class Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous.Native.setUpClass();cls.driver=previous.Native()
        for name in ('JointEnergy01','Flare02','Fire03'):
            (cls.driver.root/'Data/Effect'/(name+'.OZJ')).write_bytes(ozj_jpeg(32,32))
        cls.far_placement=Path(previous.Native.tmp.name)/'far-actors.txt'
        cls.far_placement.write_text('actor 3 124 120 0 label DemoTarget\n')
        for name in ('Piercing','Ice01','blood_storm_sword'):
            (cls.driver.root/'Data/Skill'/(name+'.bmd')).write_bytes(nf.synthetic_layout(400,actions=1,keys=(8,)))
    @classmethod
    def tearDownClass(cls):previous.Native.tearDownClass()
    def test_each_summon_consumes_ground_and_retires_without_spawning_actor(self):
        for skill in range(30,37):
            rows=self.driver.cast(skill,2,'bow',frames=65);frames=self.driver.assert_safe(rows)
            plan=next(r for r in rows if r.get('skill32'))
            self.assertEqual((plan['requests'],plan['refused']),(1,0))
            self.assertTrue(any(r['joints'] for r in frames),skill)
            self.assertEqual(frames[-1]['joints'],0)
            self.assertTrue(all(len(r['monsters'])==1 for r in frames))
    def test_penetration_child_and_four_trails_retire(self):
        for skill in (52,416):
            with patch.object(self.driver,'placement',self.far_placement):
                rows=self.driver.cast(skill,2,'bow',frames=80)
            frames=self.driver.assert_safe(rows)
            summary=next(r for r in rows if r.get('combat') is True)
            self.assertEqual(summary['unsupported'],0,summary)
            self.assertGreaterEqual(summary['joints_created'],4)
            self.assertTrue(any(r['joints'] for r in frames))
            self.assertEqual((frames[-1]['fx'],frames[-1]['joints']),(0,0))
    def test_blood_storm_body_requires_authored_owner_flag_and_retires(self):
        counts=[]
        for flag in ('0','1','invalid'):
            with patch.dict(os.environ,{'MU_SKILL33_BLOOD_OWNER':flag}):
                rows=self.driver.cast(344,1,'sword',frames=100)
            frames=self.driver.assert_safe(rows)
            summary=next(r for r in rows if r.get('combat') is True)
            self.assertEqual(frames[-1]['fx'],0)
            counts.append(summary['unsupported'])
            self.assertEqual(summary['fx_created'],2)
        self.assertEqual(counts[0],counts[2]);self.assertGreater(counts[1],counts[0])
    def test_swell_life_combines_existing_callers_and_consumers(self):
        rows=self.driver.cast(48,1,'sword',frames=100);frames=self.driver.assert_safe(rows)
        summary=next(r for r in rows if r.get('combat') is True)
        self.assertEqual(summary['unsupported'],0,summary)
        self.assertEqual(summary['joints_created'],72) # 36 requests, each emits one 0x7f78/2 child at life 19
        self.assertEqual(summary['fx_created'],2)
        self.assertEqual((frames[-1]['fx'],frames[-1]['joints']),(0,0))
    def test_target_ice_requires_separate_fixture_input_and_expires(self):
        counts=[]
        for ticks in ('0','20','invalid'):
            with patch.dict(os.environ,{'MU_SKILL33_TARGET_ICE':ticks}):
                rows=self.driver.cast(51,2,'bow',frames=90)
            frames=self.driver.assert_safe(rows)
            summary=next(r for r in rows if r.get('combat') is True)
            counts.append(summary['fx_created'])
            self.assertEqual(summary['unsupported'],0,summary)
            self.assertEqual(frames[-1]['fx'],0)
        self.assertEqual(counts[0],counts[2]);self.assertEqual(counts[1],counts[0]+2)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class Original(unittest.TestCase):
    def test_original_consumer_group(self):
        for directory in ('combat','joints','particles'):
            subprocess.run(['make','-s','-C',str(ROOT/'reconstructed'/directory)],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_effects33.py'),
                '--cases','20','--output',str(path)],check=True,cwd=ROOT,capture_output=True)
            report=json.loads(path.read_text())
        self.assertTrue(report['all_equal'],report['families'])

if __name__=='__main__':unittest.main()
