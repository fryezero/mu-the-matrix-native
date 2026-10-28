"""AUDIO-002C: actual combat/world sounds use the session reader and log."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_native_combat import write_combat_world
from test_native_audio import constant_wav
NATIVE=Path(__file__).resolve().parents[1]
class CombatAudio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-C',str(NATIVE),'build/mu-walk'],check=True,capture_output=True)
        cls.tmp=tempfile.TemporaryDirectory(prefix='audio-combat-world-');cls.folder=Path(cls.tmp.name)
        cls.root=write_combat_world(cls.folder/'game')
        cls.placement=cls.folder/'placement';cls.placement.write_text('actor 3 123 120 6 label spider\n')
        cls.players=cls.folder/'players';cls.players.write_text('player Doomed class=0x00 at=118,122 dir=2 die=20 respawn=200\n')
        wav=cls.folder/'sound.wav';wav.write_bytes(constant_wav(.125,8000))
        cls.table=cls.folder/'sounds.tsv'
        ids=[*range(0x3c,0x7c),*range(0xd2,0x200)]
        cls.table.write_text(''.join(f'sound\t{id}\t{wav}\t1\t1\t0\t0\n' for id in ids))
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def run_world(self,name,args,audio=True):
        with tempfile.TemporaryDirectory(dir=self.folder) as out:
            log=self.folder/(name+'.jsonl')
            cmd=[str(NATIVE/'build/mu-walk'),'--game-root',str(self.root),'--headless','--backend','soft',
                 '--placement',str(self.placement),'--combat','--width','64','--height','64','--every','40',
                 '--out-dir',out,'--tile','120,120','--sound-table',str(self.table),*args]
            if not audio:cmd+=['--no-audio']
            p=subprocess.run(cmd,capture_output=True,text=True,env=dict(os.environ,MU_AUDIO_CUE_LOG=str(log)))
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            rows=[json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
            sounds=[r for r in map(json.loads,log.read_text().splitlines()) if r['op']=='play' and r['handler']] if log.exists() else []
            self.assertTrue(all(s['session_tick']>0 and s['site'] for s in sounds))
            self.assertEqual([s['cue_seq'] for s in sounds],sorted(set(s['cue_seq'] for s in sounds)))
            return rows,sounds
    def test_melee_hurt_and_death_and_silent_hashes(self):
        args=['--frames','520','--combat-seed','11','--combat-script','2:attack:spider']
        on,sounds=self.run_world('fight',args)
        off,_=self.run_world('silent',args,False)
        self.assertTrue(any(s['handler']==0x1392bde and s['at_key']==-1 for s in sounds))
        self.assertTrue(any(s['handler']==0x138f92f and s['at_key']==-1 for s in sounds))
        self.assertTrue(any(s['site']==0x138fc68 and s['at_key']==0x400 for s in sounds))
        self.assertTrue(any(s['site']==0x13943e5 and s['at_key']==0x400 for s in sounds))
        a=[r['sha256'] for r in on if 'sha256' in r];b=[r['sha256'] for r in off if 'sha256' in r]
        self.assertEqual(len(a),14);self.assertEqual(a,b)
    def test_hero_and_remote_player_death(self):
        _,sounds=self.run_world('deaths',['--frames','260','--hero-hp','10','--combat-seed','11',
            '--combat-script','2:attack:spider','--players',str(self.players)])
        deaths=[s for s in sounds if s['site']==0x139442f]
        self.assertTrue(any(s['at_key']==-1 for s in deaths))
        self.assertEqual(len([s for s in deaths if s['at_key']==0x200]),1)
    def test_cast_and_end_sounds_have_distinct_provenance(self):
        for skill,site,id in [(19,0x1255f1c,0x70),(4,0x13b03eb,0x42),(17,0x13b0e08,0x76),
                             (9,0x13ad00b,0x75),(41,0x13abb36,0x73)]:
            with self.subTest(skill=skill):
                _,sounds=self.run_world(f'skill-{skill}',['--frames','60','--combat-weapon','staff',
                    '--class','0','--combat-script',f'2:skill:{skill}:spider'])
                self.assertTrue(any(s['id']==id and s['site']==site and s['at_key']==-1 for s in sounds),sounds)
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','Pinned combat audio instructions are opt-in')
    def test_original_combat_audio(self):
        report=self.folder/'original.json'
        result=subprocess.run([sys.executable,str(NATIVE.parent/'scripts/validate_audio_combat.py'),'--cases','6000',
                        '--mutations','--report',str(report)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        data=json.loads(report.read_text());self.assertEqual(data['cases'],19548)
        self.assertEqual(data['mismatches'],0);self.assertEqual(len(data['mutants']),16)
        self.assertTrue(all(v=='caught' for v in data['mutants'].values()))
if __name__=='__main__':unittest.main()
