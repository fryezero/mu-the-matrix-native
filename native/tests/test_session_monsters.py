"""VIEWPORT-MONSTER-001: monster/NPC records share the player table and routes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_session_characters as characters
NATIVE,ROOT=characters.NATIVE,characters.ROOT

class Monsters(unittest.TestCase):
    setUpClass = classmethod(characters.Characters.setUpClass.__func__)
    tearDownClass = classmethod(characters.Characters.tearDownClass.__func__)
    drive = characters.Characters.drive
    def test_monster_and_npc_frames_share_table_and_destroy_route(self):
        result,rows=self.drive(NATIVE/'fixture/scenarios/monsters-viewport.scn')
        self.assertEqual(result.returncode,0,result.stderr)
        monsters=[x for x in rows if x.get('monster_tick')==2]
        self.assertEqual([(x['key'],x['server_class'],x['model']) for x in monsters],
                         [(0x400,3,0x7ae),(0x401,251,0xa01)])
        self.assertEqual(next(x['count'] for x in rows if x.get('tick')==4 and 'count' in x),1)

    def test_mixed_batch_and_malformed_monster_atomicity(self):
        def monster(key,cls=3):
            b=bytearray(33);b[:5]=bytes([0xc2,0,33,0x13,1]);b[5:7]=key.to_bytes(2,'big')
            b[7:9]=cls.to_bytes(2,'big');b[9:13]=bytes([10,11,10,11]);b[13]=0x30
            b[21:23]=bytes([0x12,0x34]);b[23:27]=bytes([0x11,0x33,0x22,0x44]);b[27:31]=bytes([0x55,0x77,0x66,0x88])
            return b
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'mixed.scn';good=monster(1);bad=monster(2);bad[4]=2
            p.write_text('endpoint game 127.0.0.1:55902\nuse characters x=10 y=10\n'
                'at 1 characters player First class=1 at=10,10\n'
                f'at 2 send game {good.hex(" ")}\n'
                f'at 3 send game {bad.hex(" ")}\n')
            result,rows=self.drive(p)
        self.assertEqual(result.returncode,0,result.stderr)
        m=next(x for x in rows if x.get('monster_tick')==2)
        self.assertEqual((m['level'],m['max_hp'],m['hp']),(0x1234,0x11223344,0x55667788))
        for tick in (2,3):
            row=next(x for x in rows if x.get('tick')==tick and 'count' in x)
            self.assertEqual((row['count'],row['rev']),(2,2))

    def test_cache_destroy_effect_and_recreate_identity(self):
        from test_native_world import write_open_world
        from test_native_world2 import write_life
        subprocess.run(['make','-C',str(NATIVE),'build/monsters-lifecycle-host'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root=write_open_world(Path(tmp)/'root');write_life(root)
            placement=Path(tmp)/'placement.txt'
            placement.write_text('actor 3 123 122 2\nactor 251 118 118 4\nactor 873 116 118 0\n')
            scenario=Path(tmp)/'lifecycle.scn'
            b=bytearray(33);b[:14]=bytes([0xc2,0,33,0x13,1,0x84,2,0,251,120,120,120,120,0x50])
            scenario.write_text(f'endpoint game 127.0.0.1:55902\nuse monsters file={placement}\n'
                'at 2 send game c1 06 14 01 04 02\n'+f'at 3 send game {b.hex(" ")}\n')
            result=subprocess.run([str(NATIVE/'build/monsters-lifecycle-host'),str(root),str(placement),str(scenario)],
                                  capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),{'lifecycle':3,'destroyed_effects':1,'reused_identity':1})

    def test_monster_capacity_overflow_and_slot_reuse(self):
        def packet(key):
            b=bytearray(33);b[:5]=bytes([0xc2,0,33,0x13,1])
            b[5:7]=(key|0x8000).to_bytes(2,'big');b[8]=3
            b[9:13]=bytes([10,10,10,10]);b[13]=0x30
            return b.hex(' ')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'capacity.scn'
            lines=['endpoint game 127.0.0.1:55902']
            lines += [f'at {i} send game {packet(i)}' for i in range(1,402)]
            lines += ['at 402 send game c1 06 14 01 00 06', f'at 403 send game {packet(1000)}']
            p.write_text('\n'.join(lines)+'\n')
            result,rows=self.drive(p,'capacity')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(rows[0],{'capacity':400,'overflow_ignored':1,'reused_slot':5,'generation':2})

class PrivateMonsters(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','private instruction captures')
    def test_original_handler_and_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/'monsters.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_viewport_monsters.py'),
                '--cases','1000','--mutations','--output',str(report)],check=True,capture_output=True)
            data=json.loads(report.read_text())
        self.assertEqual((data['handler_cases'],data['creation_cases'],data['mismatches']),(1000,963,0))
        self.assertEqual(data['mutants']['caught'],8)
