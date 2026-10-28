"""Generated layout tables also govern the session's real journal snapshots."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_session_support import TOOL, SCENARIOS, run_tool, jnl
sys.path.insert(0, str(HERE.parents[1] / 'scripts'))
import layout_manifest


@unittest.skipUnless(TOOL.exists(), 'mu-session not built')
class LayoutSession(unittest.TestCase):
    def test_snapshot_field_boundaries_and_layout_digest(self):
        data = layout_manifest.load()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshot.mujnl'
            scenario = Path(tmp) / 'layout.scn'
            scenario.write_text('endpoint game 127.0.0.1:55901\n'
                                'use progress class=0x01 level=1 latency=0\n'
                                'join world=0 tile=10,10 angle=0 class=0x01 level=1 name=Layout slot=0\n')
            r, rows = run_tool('fixture', scenario, '--ticks', 3, '--journal', path)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(path.read_bytes()[40:72].hex(), data['sha256'])
            snapshots = jnl(rows, 'snapshot')
            if not snapshots:
                rr, dump = run_tool('journal', path)
                self.assertEqual(rr.returncode, 0, rr.stderr)
                snapshots = jnl(dump, 'snapshot')
            self.assertEqual(len(snapshots), 1)
            zones = snapshots[0]['zones']
            attr = [z for z in zones if z['name'] == 'hero.attr']
            # The larger attribute storage and every manifest field are dumped, including timers.
            record = layout_manifest.record('CharacterAttribute', data)
            self.assertEqual(sum(z['size'] for z in attr), record['size'])
            self.assertEqual({(f['offset'], f['size']) for f in record['fields']} -
                             {(z['offset'], z['size']) for z in attr}, set())
            self.assertTrue(any(z['offset'] == 0xccc and z['size'] == 0xe84 for z in attr))
