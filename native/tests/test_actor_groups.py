"""Exact generated group admission, whole census and private original comparisons."""
import collections
import csv
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_actor_groups as v

class Plans(unittest.TestCase):
    def test_checked_rows_and_exclusions(self):
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/actors')],check=True,capture_output=True)
        lib=v.library()
        with v.DECISIONS.open() as f:decisions={int(r['server_class']):r for r in csv.DictReader(f)}
        self.assertEqual(set(decisions),{int(r['server_class']) for r in v.population()})
        admitted={cl for cl,r in decisions.items() if r['decision']=='checked group body plan'}
        self.assertEqual(len(admitted),172)
        with (ROOT/'docs/research/actor-construction-census.csv').open() as f:census={int(r['server_class']):r for r in csv.DictReader(f)}
        self.assertEqual(collections.Counter(r['native'] for r in census.values()),{
            'correct bounded body plan':589+len(admitted),'incomplete/unverified special passes':355-len(admitted),'refused':80})
        for cl in range(-1,1025):
            p=v.Plan();self.assertEqual(lib.mu_actor_group_plan(cl,C.byref(p)),int(cl in admitted))
            if cl in admitted:
                self.assertEqual((p.body.server_class,p.body.flags,p.body.translate),(cl,2,1))
                self.assertTrue(p.file.startswith(b'Data/'));self.assertIn(p.textures,(b'Data/Npc',b'Data/Monster'))
                self.assertEqual(census[cl]['native'],'correct bounded body plan')
        for cl in (1,5,10,374,378,595,617,635,642,918):self.assertNotIn(cl,admitted)
        for cl,r in decisions.items():
            self.assertEqual(census[cl]['remaining_reason'],r['reason'])
            self.assertEqual(bool(r['reason']),cl not in admitted)
        with (ROOT/'docs/research/actor-missing-plan-groups.csv').open() as f:groups=list(csv.DictReader(f))
        selectors=[int(cl) for g in groups for cl in g['selectors'].split(';')]
        self.assertEqual(len(selectors),905);self.assertEqual(len(set(selectors)),905)
        self.assertEqual(sum(int(g['count']) for g in groups if g['state']=='incomplete'),355-len(admitted))

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires private-env.sh')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/'report.json'
            run=subprocess.run([sys.executable,str(ROOT/'scripts/validate_actor_groups.py'),'--cases','24','--output',str(report)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout[-4000:]+run.stderr[-3000:])
            self.assertTrue(json.loads(report.read_text())['all_equal'])
