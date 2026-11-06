"""Session vitality reaches the HUD without demonstration animation."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_app_polish2 as v

class AppPolish2(unittest.TestCase):
    def test_session_values_and_idle_movie(self):
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);log=work/'vitals.log'
            old=os.environ.get('MUGFX_STUB_LOG');os.environ['MUGFX_STUB_LOG']=str(log)
            try:
                p=v.native(work)
                words=[390,180,1100,200,40,52,20,25,9000,8000,7000,6000]
                expected=dict(zip(v.FIELDS,[390,1100,180,200,40,52,20,25]))
                self.assertEqual(p(1,words),expected)
                initial=len([x for x in log.read_text().splitlines() if '.setHPMP ' in x])
                for _ in range(100):self.assertEqual(p(1,words),expected)
                calls=[json.loads(line.split(' ',2)[2])[0] for line in log.read_text().splitlines() if '.setHPMP ' in line]
                self.assertEqual(len(calls),initial) # no repeated update while the session is unchanged
                self.assertEqual(calls[-1],{'isToxic':False,**expected})
                words[0]=371
                self.assertEqual(p(1,words)['hp'],371)
                master=p(0x21,words)
                self.assertEqual([master[x] for x in ('maxHp','maxMp','ShieldMax','SkillManaMax')],words[8:])
                # Raw session zero/overflow values are displayed, never locally clamped or regenerated.
                for x in (0,-1,2147483647):
                    words[0]=x;self.assertEqual(p(1,words)['hp'],x)
                p.fallback(1)
                words=[377,180,0,0,40,0,20,0,0,0,0,0]
                self.assertEqual(p(1,words),dict(zip(v.FIELDS,[377,1100,180,200,40,52,20,25])))
                words[2]=1200
                self.assertEqual(p(1,words)['maxHp'],1200)
                p.close()
            finally:
                if old is None:os.environ.pop('MUGFX_STUB_LOG',None)
                else:os.environ['MUGFX_STUB_LOG']=old

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private original instructions')
    def test_original_body(self):
        from types import SimpleNamespace
        r=v.run(SimpleNamespace(text=None,data=None,section3=None,cases=20,mutants=False))
        self.assertEqual(r['mismatches'],0)
