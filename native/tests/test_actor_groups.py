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
        self.assertEqual(len(admitted),186)
        with (ROOT/'docs/research/actor-construction-census.csv').open() as f:census={int(r['server_class']):r for r in csv.DictReader(f)}
        self.assertEqual(collections.Counter(r['native'] for r in census.values()),{
            'correct bounded body plan':589+len(admitted),'incomplete/unverified special passes':355-len(admitted),'refused':80})
        for cl in range(-1,1025):
            p=v.Plan();self.assertEqual(lib.mu_actor_group_plan(cl,C.byref(p)),int(cl in admitted))
            if cl in admitted:
                self.assertEqual((p.body.server_class,p.body.flags,p.body.translate),(cl,2,1))
                self.assertTrue(p.file.startswith(b'Data/'));self.assertIn(p.textures,(b'Data/Npc',b'Data/Monster'))
                self.assertEqual(census[cl]['native'],'correct bounded body plan')
        for cl in (22,40,41,70,275,374,378,546,595,617,635,642,866,918):self.assertNotIn(cl,admitted)
        for cl in (1,5,10,151,433):self.assertIn(cl,admitted)
        for cl,r in decisions.items():
            self.assertEqual(census[cl]['remaining_reason'],r['reason'])
            self.assertEqual(bool(r['reason']),cl not in admitted)
        with (ROOT/'docs/research/actor-missing-plan-groups.csv').open() as f:groups=list(csv.DictReader(f))
        selectors=[int(cl) for g in groups for cl in g['selectors'].split(';')]
        self.assertEqual(len(selectors),905);self.assertEqual(len(set(selectors)),905)
        self.assertEqual(sum(int(g['count']) for g in groups if g['state']=='incomplete'),355-len(admitted))

    def test_caller_requests(self):
        """RENDER-ACTORS-008: generated sprite requests, compiled light and the published table."""
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/actors')],check=True,capture_output=True)
        lib=v.library()
        with v.DECISIONS.open() as f:decisions={int(r['server_class']):r for r in csv.DictReader(f)}
        admitted={cl for cl,r in decisions.items() if r['decision']=='checked group body plan'}
        with v.REQUESTS.open() as f:table=list(csv.DictReader(f))
        published=collections.Counter()
        for r in table:
            self.assertIn(int(r['server_class']),decisions)
            self.assertEqual(r['decision'],decisions[int(r['server_class'])]['decision'])
            if r['phase']=='caller':published[int(r['server_class'])]+=int(r['count'])
        total=0;classes=0
        for cl in range(-1,1025):
            first=C.POINTER(v.Fx)();count=lib.mu_actor_caller_fx_plan(cl,C.byref(first))
            if not count:
                self.assertEqual(lib.mu_actor_caller_fx_random(cl),0);continue
            self.assertIn(cl,admitted);self.assertEqual(published[cl],count);total+=count;classes+=1
            for i in range(count):
                fx=first[i];self.assertEqual(fx.server_class,cl);self.assertIn(fx.light_kind,(0,1,2))
                self.assertIn(fx.owner,(0,1));self.assertGreaterEqual(fx.bone,0)
            self.assertEqual(lib.mu_actor_caller_fx_random(cl),int(any(first[i].light_kind==1 for i in range(count))))
        self.assertEqual((classes,total),(33,73))
        # Classes 1 and 46: the sword flicker and the two-bone pulse, without private data.
        first=C.POINTER(v.Fx)();self.assertEqual(lib.mu_actor_caller_fx_plan(1,C.byref(first)),1)
        self.assertEqual((first[0].bitmap,first[0].bone,first[0].light_kind,first[0].owner,first[0].axes),(0x7ef7,19,1,1,4))
        out=(C.c_float*3)();lib.mu_actor_caller_fx_light(C.byref(first[0]),777.0,12345,C.byref(out))
        f=C.c_float;self.assertEqual(out[0],f(f(f(85.0).value*f(0.01).value).value*f(0.3).value).value)
        self.assertEqual(lib.mu_actor_caller_fx_plan(46,C.byref(first)),6)
        self.assertEqual([first[i].bone for i in range(6)],[30,39,30,39,30,39])
        lib.mu_actor_caller_fx_light(C.byref(first[0]),0.0,7,C.byref(out))
        self.assertEqual([round(x,6) for x in out],[0.7,0.42,0.28])
        p=v.Plan();self.assertEqual(lib.mu_actor_group_plan(145,C.byref(p)),1);self.assertEqual(p.link_effect_mask,1)
        self.assertEqual(lib.mu_actor_group_plan(13,C.byref(p)),1);self.assertEqual(p.link_effect_mask,0)

@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires private-env.sh')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/'report.json'
            run=subprocess.run([sys.executable,str(ROOT/'scripts/validate_actor_groups.py'),'--cases','24','--output',str(report)],
                cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout[-4000:]+run.stderr[-3000:])
            self.assertTrue(json.loads(report.read_text())['all_equal'])
