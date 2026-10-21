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


def stub_library(folder):
    """The stand-in libmugfx (native/tests/gfx_stub_mugfx.c) and a movie directory with an empty
    CharacterSelect.swf: CI has no Rust and no client movies (NATIVE-CHARSEL-003)."""
    folder = Path(folder)
    lib = folder / ('libmugfx_stub.dylib' if sys.platform == 'darwin' else 'libmugfx_stub.so')
    if not lib.exists():
        subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-O1', '-shared', '-fPIC', '-o', str(lib),
                        str(HERE / 'gfx_stub_mugfx.c')], check=True)
    movies = folder / 'movies'
    movies.mkdir(exist_ok=True)
    for name in ('CharacterSelect', 'Caution', 'winSystemMenu'):   # NATIVE-CHARCREATE-001: the boxes, the menu
        (movies / f'{name}.swf').write_bytes(b'')
    return lib, movies


class CharacterListTests(Build):
    """NATIVE-CHARSEL-003: the GFx character list through the stand-in library."""

    def run_list(self, name, *args):
        lib, movies = stub_library(self.tmp.name)
        log = Path(self.tmp.name) / f'{name}.log'
        stub_log = Path(self.tmp.name) / f'{name}.stub'
        for p in (log, stub_log):
            if p.exists():
                p.unlink()
        env = {**os.environ, 'MU_GFX_LIB': str(lib), 'MUGFX_STUB_LOG': str(stub_log)}
        r = subprocess.run([str(SHELL), '--game-root', str(self.root), '--no-audio', '--session', str(self.session),
                            '--gfx', str(movies), '--gfx-log', str(log), *[str(a) for a in args]],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        summary = next(json.loads(x) for x in r.stdout.splitlines() if x.startswith('{') and '"summary"' in x)
        return summary, log.read_text().splitlines(), stub_log.read_text().splitlines()

    def test_auto_flow_selects_and_enters_through_the_list(self):
        summary, lines, stub = self.run_list('auto', '--auto', '--frames', '300', '--width', '640', '--height', '480')
        self.assertEqual(scenes(summary)[:4], [(2, 3), (3, 5), (5, 4), (4, 6)])
        # --auto clicks row 1 and double-clicks it: slot 1 (class 0x22) enters
        self.assertEqual((summary['hero_slot'], summary['hero_class']), (1, 0x22))
        self.assertGreaterEqual(summary['charsel']['gfx_enters'], 1)
        self.assertIn('callback UIInit ["g_mcCharacterSelect"]', lines)
        self.assertTrue(any(x.startswith('callback OnCharSelectedClick [1.0]') for x in lines))
        self.assertTrue(any(x.startswith('callback OnCharSelectedDClick [1.0]') for x in lines))
        rows = next(json.loads(x.split(' ', 2)[2])[0] for x in stub if '.SetSelectText ' in x)
        self.assertEqual([r['type'] for r in rows], [0, 0, 0] + [1] * 7)
        self.assertEqual(rows[2]['textName'], "<font color='#FFCC19'>Charlie</font><br>")
        # the window's initialisation answers UIInit before the list (0x00b4915b)
        methods = [x.split(' ')[1].split('.')[-1] for x in stub if x.startswith('CharacterSelect ')]
        self.assertLess(methods.index('InitText'), methods.index('SetSelectText'))
        self.assertIn('InitClassInfo', methods)

    def test_empty_row_is_an_offline_create_request(self):
        summary, lines, _ = self.run_list('create', '--frames', '60', '--width', '640', '--height', '480',
                                          '--script', '10:enter 14:enter 30:click:row:7')
        self.assertEqual(summary['scene'], 5)
        self.assertEqual(summary['charsel']['create_requests'], 1)
        self.assertIn('line call 00b49bf4 1 ', lines)
        self.assertEqual(summary['selected_hero'], -1)

    def test_double_click_beside_the_character_does_not_enter(self):
        summary, _, _ = self.run_list('miss', '--frames', '60', '--width', '640', '--height', '480',
                                      '--script', '10:enter 14:enter 30:dblclick:5,5')
        self.assertEqual(summary['scene'], 5)
        self.assertGreaterEqual(summary['charsel']['double_clicks'], 1)
        self.assertGreater(summary['charsel']['picks'], 10)


class CharacterCreateTests(Build):
    """NATIVE-CHARCREATE-001: the create panel, the delete flow and the menu through the stand-in library (the
    reconstructed window code over synthetic data); OFFLINE DEMO answers from a store in the temporary folder."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logo = Path(cls.root) / 'Data' / 'Logo'   # a synthetic bust as the Slayer's NewFace10.bmd
        logo.mkdir(parents=True, exist_ok=True)
        model = nf.write_textured_model(logo, seed=4)
        model.rename(logo / 'NewFace10.bmd')
        lang = Path(cls.tmp.name) / 'lang'          # synthetic name tables (scripts/live_lang_filters.py format)
        lang.mkdir(exist_ok=True)
        (lang / 'filtername.txt').write_text('GM\nwebzen\n')
        (lang / 'filter.txt').write_text('SELECT\n')
        (lang / 'globaltext.txt').write_text('5526\tSlayer (table)\n5786\tGun Crusher (table)\n')

    def flow(self, name, script, *args, store=None, lang=False):
        lib, movies = stub_library(self.tmp.name)
        folder = self.out(name)
        log, stub_log = folder / 'gfx.log', folder / 'stub.log'
        for p in (log, stub_log):
            if p.exists():
                p.unlink()
        env = {**os.environ, 'MU_GFX_LIB': str(lib), 'MUGFX_STUB_LOG': str(stub_log)}
        env.pop('MU_LANG_DIR', None)
        if lang:
            env['MU_LANG_DIR'] = str(Path(self.tmp.name) / 'lang')
        store = store or folder / 'store.txt'
        r = subprocess.run([str(SHELL), '--game-root', str(self.root), '--no-audio', '--session', str(self.session),
                            '--gfx', str(movies), '--gfx-log', str(log), '--store', str(store), '--width', '640',
                            '--height', '480', '--script', script, *[str(a) for a in args]],
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        rows = [json.loads(x) for x in r.stdout.splitlines() if x.startswith('{')]
        summary = next(x for x in rows if x.get('summary'))
        frames = [x for x in rows if 'png' in x]
        return summary, log.read_text().splitlines(), stub_log.read_text().splitlines(), store, frames, r.stderr

    def lists(self, stub):
        return [json.loads(x.split(' ', 2)[2])[0] for x in stub if '.SetSelectText ' in x]

    def test_create_through_the_panel(self):
        summary, lines, stub, store, frames, _ = self.flow(
            'create', '10:enter 14:enter 30:click:create 40:click:class:9 50:text:Nova 60:click:createok',
            '--frames', '90', '--out-dir', self.out('create-frames'), '--every', '45', lang=True)
        cc = summary['charcreate']
        self.assertEqual((cc['creates'], cc['created'], cc['rebuilds'], cc['characters']), (1, 1, 1, 4))
        # SetSelectedClass(9): NewFace10 (model 0x135 + 9), drawn while the panel was open; closing it shows
        # class 1 again (0x00b49bf4(0): SetClassInfo(1))
        self.assertEqual(cc['preview_class'], 1)
        self.assertGreater(cc['preview_frames'], 0)
        drawn = [f for f in frames if f['frame'] == 45][0]['png']
        self.assertTrue(Path(drawn).exists())
        self.assertIn('line call 00b4a442 9 ', lines)
        self.assertIn('line call 0137d8a1 p 318 0 0 00000000 ', lines)
        self.assertIn('line call 009a466c "Nova" 144 ', lines)   # (9 << 4) + skin 0
        # the store keeps the new character in the first free slot; the scene was created again with it
        self.assertIn('3 0x09 1 Nova', store.read_text())
        rows = self.lists(stub)[-1]
        self.assertEqual([r['type'] for r in rows[:5]], [0, 0, 0, 0, 1])
        self.assertEqual(rows[3]['textJob'], 'Slayer (table)')   # the class-name switch's code 9: GlobalText 5526
        self.assertTrue(any('.UpdateCreateCount ["GT6193"]' in x for x in stub))
        self.assertEqual(summary['scene'], 5)

    def test_name_refusals(self):
        script = '10:enter 14:enter 30:click:create 40:text:{} 50:click:createok'
        cases = (('Ab', 'GT390', False), ('xGMx', 'GT1715', True), ('ADSELECT', 'GT1715', True),
                 ('sym!bol', 'GT391', False))
        for typed, text, lang in cases:
            with self.subTest(typed=typed):
                summary, lines, _, store, _, _ = self.flow(f'refuse-{len(text)}-{typed}', script.format(typed),
                                                           '--frames', '70', lang=lang)
                cc = summary['charcreate']
                self.assertEqual((cc['creates'], cc['caution_open']), (0, 1))
                self.assertEqual(cc['last_message'], text)
                self.assertTrue(any(x.startswith(f'line call 00b3967c w 100 "{text}"') for x in lines))
                self.assertFalse(store.exists())   # nothing changed: nothing written
        # without the tables the filters do not apply (GM is a valid name then)
        summary, _, _, _, _, _ = self.flow('nofilter', script.format('xGMx'), '--frames', '80')
        self.assertEqual(summary['charcreate']['created'], 1)

    def test_delete_flow_and_password(self):
        script = ('10:enter 14:enter 30:click:row:1 40:click:delete 50:click:msgok 60:click:msgok 70:text:secret '
                  '80:click:msgok 95:click:msgok')
        summary, lines, stub, store, _, err = self.flow('delete', script, '--frames', '110')
        cc = summary['charcreate']
        self.assertEqual((cc['deletes'], cc['deleted'], cc['rebuilds'], cc['characters']), (1, 1, 1, 2))
        self.assertEqual(cc['last_message'], 'GT1714')
        self.assertTrue(any(x.startswith('line call 00b39648 w 102 "GT3751\\nGT3752"') for x in lines))
        self.assertTrue(any(x.startswith('line call 00b3974a w 103 "GT1713" "" 20') for x in lines))
        # the password reaches nothing: not the log, not the store
        self.assertIn('line call 00b4c76a (delete request) ', lines)
        self.assertFalse(any('secret' in x for x in lines))
        self.assertNotIn('secret', store.read_text())
        self.assertNotRegex(store.read_text(), r'(?m)^1 ')
        self.assertEqual([r['type'] for r in self.lists(stub)[-1][:3]], [0, 1, 0])

    def test_cancel_and_esc_close_the_panel(self):
        summary, lines, _, _, _, _ = self.flow('cancel', '10:enter 14:enter 30:click:create 40:click:createcancel',
                                              '--frames', '60')
        self.assertEqual(summary['charcreate']['create_open'], 0)
        self.assertIn('line call 00b4c806 -1 ', lines)
        summary, _, _, _, _, _ = self.flow('esc', '10:enter 14:enter 30:click:create 40:esc', '--frames', '60')
        self.assertEqual((summary['charcreate']['create_open'], summary['charcreate']['menu_open']), (0, 0))

    def test_menu(self):
        summary, lines, stub, _, _, _ = self.flow('menu', '10:enter 14:enter 30:esc 40:click:menu:server',
                                                  '--frames', '60')
        self.assertIn((5, 3), scenes(summary))           # Select Server: the offline logout answer
        self.assertIn('line menu invoke SceneChange [5] ', lines)
        self.assertTrue(any('winSystemMenu _level0.mcSystemMenu.openWindow' in x for x in stub))
        summary, _, _, _, _, _ = self.flow('exit', '10:enter 14:enter 30:esc 40:click:menu:exit', '--frames', '400')
        self.assertLess(summary['frames'], 400)            # Exit Game quits after the countdown box
        self.assertEqual(summary['charcreate']['last_message'], 'GT380')

    def test_store_survives_and_empty_list_opens_the_panel(self):
        folder = self.out('store')
        store = folder / 'store.txt'
        store.write_text('created 2000-01-01 4\n5 0x0a 7 Gunner\n')   # another day: the count restarts
        summary, _, stub, _, _, _ = self.flow('store', '10:enter 14:enter', '--frames', '40', store=store, lang=True)
        rows = self.lists(stub)[-1]
        self.assertEqual(rows[5]['textJob'], 'Gun Crusher (table)')   # code 10: GlobalText 5786
        self.assertTrue(any('.UpdateCreateCount ["GT6193"]' in x for x in stub))
        store.write_text('created 2000-01-01 0\n')
        summary, _, _, _, _, _ = self.flow('store', '10:enter 14:enter', '--frames', '40', store=store)
        self.assertEqual((summary['charcreate']['characters'], summary['charcreate']['create_open']), (0, 1))


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
