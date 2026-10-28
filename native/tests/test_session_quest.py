"""SESSION-QUEST-001: body boundary, domains and headless integration."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_session_support import NATIVE, TOOL, run_tool, jnl, first
from test_native_world import write_open_world
from test_native_quest import QUESTS, STRINGS, guide_fixture, GUIDE_STRINGS

class QuestSession(unittest.TestCase):
    def test_opaque_bodies_are_journaled_and_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'quest-opaque.scn'
            path.write_text('endpoint game 127.0.0.1:55903\nuse quest\njoin world=0 tile=1,1\n'
                            'at 2 send game c1 0a f6 70 00 00 00 00 00 00\n'
                            'at 3 send game c1 0a f6 71 00 00 00 00 00 00\n'
                            'expect undecodable = 2\nexpect unbound = 0\n')
            result,rows=run_tool('fixture',path,'--ticks',5)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            frames=jnl(rows,'frame_in')
            self.assertEqual([f['decode'] for f in frames],['body_undecoded']*2)
            self.assertEqual([f['result'] for f in frames],['body_undecoded']*2)
            self.assertEqual([f['sub'] for f in frames],[0x70,0x71])
            self.assertEqual(first(rows,'status')['undecodable'],2)

    def test_headless_walk_receives_guide_state_at_quest_tick(self):
        import subprocess,json
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp); root=folder/'game'; write_open_world(root)
            for name,text in [('quests.tsv',QUESTS),('queststrings.tsv',STRINGS),
                              ('guidequest.tsv',guide_fixture()),('guidestrings.tsv',GUIDE_STRINGS)]:
                (folder/name).write_text(text)
            demo=folder/'npc.txt';demo.write_text('guide 11:0:1\n')
            process=subprocess.run([str(NATIVE/'build/mu-walk'),'--game-root',str(root),'--npc-demo',str(demo),
                                    '--backend','soft','--frames','30','--every','100','--width','64','--height','64',
                                    '--out-dir',str(folder/'renders')],capture_output=True,text=True,
                                    env=dict(os.environ,MU_LANG_DIR=str(folder), MU_QUEST_SCENARIO=str(NATIVE/'fixture/scenarios/quest-progress.scn')))
            self.assertEqual(process.returncode,0,process.stderr)
            rows=[json.loads(line) for line in process.stdout.splitlines() if line.startswith('{')]
            quest=first(rows,'quest')
            self.assertEqual(quest['answers'],4)
            self.assertEqual(quest['active'],[dict(quest=7,state=2,count=3)])
            self.assertEqual((quest['unbound'],quest['undecodable']),(0,0))

if __name__=='__main__': unittest.main()
