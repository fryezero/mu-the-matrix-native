"""mu-client scene flow (NATIVE-SHELL-001) checks.

Portable (synthetic data only): a synthetic game tree with Data/World1 (the
walk-around fixture of test_native_world), Data/World94 and Player.bmd (the
character-select fixture of test_native_charsel), and an offline session of
synthetic servers and characters, run through `mu-shell` (headless software):
  * the scene flow follows the client's SceneFlag values 2 -> 3 -> 5 -> 4 -> 6,
    Esc returns 6 -> 5, and a second Enter enters the world again;
  * the title shows its ten startup frames and the loading scene one frame;
  * the login needs a chosen server and the OFFLINE DEMO panel (any input);
  * the world is entered with the class the start-loading routine copied
    into the Hero from the chosen slot, at the session's join position;
  * runs are deterministic; malformed sessions are refused; a world that
    does not load returns to character select.
`mu-client --headless --backend gl` is checked when SDL2 and an offscreen
context exist. Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): the
committed demo session over the installed client data.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_charsel import write_world94  # noqa: E402
from test_native_world import write_open_world  # noqa: E402

SHELL = NATIVE / 'build/mu-shell'
CLIENT = NATIVE / 'build/mu-client'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')

SERVERS = """notice synthetic server list
group left 0 1 Synthetic|first group
server 10 0 S-1
server 140 1 S-closed
server 40 2 S-3
"""
CHARACTERS = """0 0x00 10 Alpha
1 0x22 20 Bravo
2 0x03 30 Charlie
"""


def write_root(root):
    write_open_world(root)
    write_world94(root)
    interface = Path(root) / 'Data' / 'Interface'
    interface.mkdir(parents=True, exist_ok=True)
    # the title's webzen logo (0x7b85, drawn unscaled at 16,8) as a synthetic TGA
    (interface / 'New_lo_webzen_logo.OZT').write_bytes(nf.ozt(nf.tga(64, 64, 11)))
    return root


def write_session(folder, joins='join 0 0 120,120\njoin 1 0 128,128 90\n', extra=''):
    folder = Path(folder)
    (folder / 'servers.txt').write_text(SERVERS)
    (folder / 'characters.txt').write_text(CHARACTERS)
    (folder / 'session.txt').write_text('servers servers.txt\ncharacters characters.txt\n' + joins + extra)
    return folder / 'session.txt'


def run(root, *args, tool=SHELL, check=True):
    result = subprocess.run([str(tool), '--game-root', str(root), '--no-audio', *[str(a) for a in args]],
                            capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'{tool.name} failed ({result.returncode}): {result.stderr[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    frames = [r for r in rows if 'frame' in r and not r.get('summary')]
    summary = next((r for r in rows if r.get('summary')), None)
    return frames, summary, result


def scenes(summary):
    return [tuple(int(v) for v in t.split(' at ')[0].split(' -> ')) for t in summary['transitions']]


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_root(Path(cls.tmp.name) / 'root')
        cls.session = write_session(Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def out(self, name):
        path = Path(self.tmp.name) / name
        path.mkdir(exist_ok=True)
        return path


class ShellFlowTests(Build):
    def test_full_flow_follows_the_client_scene_states(self):
        frames, summary, _ = run(self.root, '--session', self.session, '--auto', '--frames', '300',
                                 '--out-dir', self.out('flow'), '--width', '320', '--height', '240')
        self.assertEqual(scenes(summary), [(2, 3), (3, 5), (5, 4), (4, 6), (6, 5), (5, 4), (4, 6)])
        self.assertEqual(summary['presents'], 12)                 # 10 title frames (progress 0..9) + 2 loading frames
        self.assertEqual(summary['visits'], {'3': 1, '5': 2, '6': 2})
        self.assertEqual(summary['protocol'], 0x33)               # the list "arrived" (offline session)
        self.assertEqual(summary['logins'], 1)
        self.assertEqual(summary['server'], [0, 0])
        # --auto steps right once: slot 1 (class 0x22) is copied into the Hero by start loading
        self.assertEqual((summary['hero_slot'], summary['hero_class'], summary['selected_hero']), (1, 0x22, 1))
        self.assertEqual(summary['world'], 0)
        tags = {(f['scene'], f['tag']) for f in frames}
        self.assertIn((2, 'present01'), tags)
        self.assertIn((6, 'frame'), tags)
        self.assertEqual(sum(1 for f in frames if f['scene'] == 2 and f['tag'].startswith('present')), 10)

    def test_login_needs_a_server_and_the_offline_panel(self):
        # no clicks: Enter picks the first open server (native shortcut), a second Enter logs in
        _, summary, _ = run(self.root, '--session', self.session, '--frames', '40', '--script', '10:enter')
        self.assertEqual(summary['scene'], 3)                     # panel shown, not logged in
        self.assertEqual((summary['logins'], summary['server']), (0, [0, 0]))
        _, summary, _ = run(self.root, '--session', self.session, '--frames', '40',
                            '--script', '10:enter 14:text:abc 18:enter')
        self.assertEqual(scenes(summary)[:2], [(2, 3), (3, 5)])
        self.assertEqual(summary['logins'], 1)

    def test_escape_twice_in_the_login_scene_quits(self):
        _, summary, _ = run(self.root, '--session', self.session, '--frames', '200', '--script', '10:esc 20:esc')
        self.assertLess(summary['frames'], 30)
        self.assertEqual(summary['scene'], 3)

    def test_escape_in_character_select_returns_to_the_servers(self):
        _, summary, _ = run(self.root, '--session', self.session, '--frames', '60',
                            '--script', '10:enter 14:enter 30:esc')
        self.assertEqual(scenes(summary), [(2, 3), (3, 5), (5, 3)])
        self.assertEqual(summary['protocol'], 0)

    def test_join_position_and_slot_from_the_session(self):
        _, summary, _ = run(self.root, '--session', self.session, '--frames', '80',
                            '--script', '10:enter 14:enter 30:enter')
        self.assertEqual(scenes(summary), [(2, 3), (3, 5), (5, 4), (4, 6)])
        self.assertEqual((summary['hero_slot'], summary['hero_class']), (0, 0x00))

    def test_world_that_does_not_load_returns_to_character_select(self):
        session = write_session(self.out('missing'), joins='join 0 7 100,100\n')
        _, summary, _ = run(self.root, '--session', session, '--frames', '80', '--script', '10:enter 14:enter 30:enter')
        self.assertEqual(scenes(summary), [(2, 3), (3, 5), (5, 4), (4, 6), (6, 5)])
        self.assertIn('world 7', summary['status'])

    def test_runs_are_deterministic(self):
        a, _, _ = run(self.root, '--session', self.session, '--auto', '--frames', '120', '--every', '20',
                      '--out-dir', self.out('det-a'), '--width', '256', '--height', '192')
        b, _, _ = run(self.root, '--session', self.session, '--auto', '--frames', '120', '--every', '20',
                      '--out-dir', self.out('det-b'), '--width', '256', '--height', '192')
        self.assertEqual([f['sha256'] for f in a], [f['sha256'] for f in b])

    def test_built_in_session(self):
        _, summary, _ = run(self.root, '--frames', '60', '--script', '10:enter 14:enter')
        self.assertEqual(scenes(summary)[:2], [(2, 3), (3, 5)])

    def test_bad_sessions_are_refused(self):
        folder = self.out('bad')
        for text, message in (('servers nothere.txt\n', 'cannot read'), ('colour blue\n', 'unknown key'),
                              ('join 0 0 300,1\n', 'expected join'), ('join 11 0 1,1\n', 'expected join')):
            (folder / 'session.txt').write_text(text)
            _, _, result = run(self.root, '--session', folder / 'session.txt', '--frames', '5', check=False)
            self.assertNotEqual(result.returncode, 0, text)
            self.assertIn(message, result.stderr, text)
        (folder / 'servers.txt').write_text('server 1 1 orphan\n')
        (folder / 'session.txt').write_text('servers servers.txt\n')
        _, _, result = run(self.root, '--session', folder / 'session.txt', '--frames', '5', check=False)
        self.assertIn('after a group', result.stderr)


class WindowToolTests(Build):
    def test_gl_headless(self):
        try:
            subprocess.run(['make', '-C', str(NATIVE), 'client'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.skipTest('SDL2/OpenGL client not buildable here')
        frames, summary, result = run(self.root, '--headless', '--backend', 'gl', '--session', self.session,
                                      '--auto', '--frames', '200', tool=CLIENT, check=False)
        if result.returncode and 'headless GL' in result.stderr:
            self.skipTest('no offscreen GL context')
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertEqual(scenes(summary)[:4], [(2, 3), (3, 5), (5, 4), (4, 6)])


@unittest.skipUnless(PRIVATE, 'private: needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateDemoSessionTests(unittest.TestCase):
    def test_demo_session_over_the_installed_client(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        root = os.environ['MU_GAME_ROOT']
        with tempfile.TemporaryDirectory() as folder:
            frames, summary, _ = run(root, '--session', NATIVE / 'client/demo-session.txt', '--auto', '--frames', '300',
                                     '--every', '50', '--width', '640', '--height', '480', '--out-dir', folder)
        self.assertEqual(scenes(summary), [(2, 3), (3, 5), (5, 4), (4, 6), (6, 5), (5, 4), (4, 6)])
        self.assertEqual((summary['hero_slot'], summary['hero_class'], summary['world']), (1, 0x01, 0))
        self.assertEqual(summary['presents'], 12)
        self.assertEqual(summary['status'], '')
        title = [f for f in frames if f['scene'] == 2 and f['tag'].startswith('present')]
        self.assertEqual(len({f['sha256'] for f in title}), 10)   # the lo_lo gauge grows every step


if __name__ == '__main__':
    unittest.main()
