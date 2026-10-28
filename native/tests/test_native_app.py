"""Mu The Matrix Native Preview.app (NATIVE-APP-001) checks.

macOS only (swiftc, codesign, install_name_tool, SDL2 for mu-client); skipped elsewhere. The app is built
into a temporary directory (native/app/Makefile, B=...) with the stand-in libmugfx (tests/gfx_stub_mugfx.c)
as its GFx library. Portable (synthetic data only):
  * bundle layout, Info.plist, an ad-hoc signature that verifies strictly and deeply, no hardened runtime
    (the launcher loads the network guard with DYLD_INSERT_LIBRARIES);
  * self-contained: no Mach-O in the bundle loads a library outside /System, /usr/lib and the bundle;
  * no network imports in mu-client, the launcher and the bundled libraries; --check-bundle passes;
  * the guard (libmu-nonet) refuses AF_INET/AF_INET6 sockets and name lookups and writes its report;
  * the first-run setup copies a synthetic scratch folder into Native Data and leaves the read-only game
    folder unchanged;
  * the launch plan: every feature on, the GFx interface when the library and movies exist, the offline
    label and window title, a window fitting the screen; the settings' toggles and size;
  * the headless smoke: the whole flow (title -> login -> character select -> loading -> world) through the
    bundled mu-client under the guard, which loads and sees no network call; the log lands in the log folder.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): the smoke over the installed game with headless GL.
"""
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_shell import write_root, write_session  # noqa: E402

NAME = 'Mu The Matrix Native Preview'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
NETWORK_IMPORTS = {'_socket', '_connect', '_connectx', '_getaddrinfo', '_gethostbyname', '_sendto', '_bind',
                   '_listen', '_accept'}


def tool(name):
    return shutil.which(name) is not None


MACOS = sys.platform == 'darwin' and tool('xcrun') and tool('codesign') and tool('sdl2-config')


def macho_files(app):
    for p in sorted(app.rglob('*')):
        if p.is_file() and not p.is_symlink():
            with open(p, 'rb') as f:
                magic = f.read(4)
            if magic in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe'):
                yield p


def snapshot(root):
    return sorted((str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns) for p in Path(root).rglob('*'))


@unittest.skipUnless(MACOS, 'macOS with the Command Line Tools and SDL2 only')
class PreviewApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        subprocess.run(['make', '-C', str(NATIVE), 'client'], check=True, capture_output=True)
        cls.stub = cls.dir / 'libmugfx_stub.dylib'
        subprocess.run(['clang', '-std=c11', '-O1', '-shared', '-fPIC', '-o', str(cls.stub),
                        str(HERE / 'gfx_stub_mugfx.c')], check=True, capture_output=True)
        build = subprocess.run(['make', '-C', str(NATIVE / 'app'), f'B={cls.dir / "build"}', f'MUGFX_LIB={cls.stub}'],
                               capture_output=True, text=True)
        if build.returncode:
            raise AssertionError('app build failed:\n' + build.stdout[-3000:] + build.stderr[-3000:])
        cls.build_log = build.stdout
        cls.app = cls.dir / 'build' / f'{NAME}.app'
        cls.launcher = cls.app / 'Contents/MacOS/MuNativePreview'
        # a read-only synthetic game folder and a synthetic scratch folder
        cls.root = write_root(cls.dir / 'root')
        (cls.dir / 'session').mkdir()
        cls.session = write_session(cls.dir / 'session')                  # synthetic characters (no item files)
        cls.scratch = cls.dir / 'scratch'
        (cls.scratch / 'lang').mkdir(parents=True)
        (cls.scratch / 'lang' / 'notes.txt').write_text('synthetic\n')
        (cls.scratch / 'lang' / 'tools').mkdir()                      # folders are not copied
        objects = cls.scratch / 'objects/live/plain'
        objects.mkdir(parents=True)
        (objects / 'EncTerrain99.plain').write_bytes(b'\0' * 4)      # a world the flow never enters
        (objects / 'EncTerrain99.hidden').write_text('1\n')
        (objects / 'README').write_text('not copied\n')
        movies = cls.scratch / 'npc/movies'
        movies.mkdir(parents=True)
        for m in ('base', 'main', 'Chat'):
            (movies / f'{m}.swf').write_bytes(b'')                    # names only (the stub library)
        (cls.scratch / 'audio/tables').mkdir(parents=True)
        (cls.scratch / 'audio/tables/audio-tables.tsv').write_text('# synthetic\n')
        for p in [cls.root, *Path(cls.root).rglob('*')]:
            p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        cls.root_before = snapshot(cls.root)

    @classmethod
    def tearDownClass(cls):
        for p in [cls.root, *Path(cls.root).rglob('*')]:
            if p.is_dir():
                p.chmod(p.stat().st_mode | stat.S_IWUSR)
        cls.tmp.cleanup()

    def env(self, name, **extra):
        base = self.dir / name
        env = {k: v for k, v in os.environ.items() if not k.startswith(('MU_NATIVE_', 'MU_LANG', 'MU_GFX'))}
        env.update(MU_NATIVE_SUPPORT_DIR=str(base / 'support'), MU_NATIVE_LOG_DIR=str(base / 'logs'),
                   MU_NATIVE_GAME_ROOT=str(self.root), MU_NATIVE_SCRATCH=str(self.scratch),
                   MU_NATIVE_PYTHON='/nonexistent/python3', MU_NATIVE_SESSION=str(self.session))
        env.update(extra)
        return env, base

    def launch(self, env, *args, check=True, timeout=300):
        r = subprocess.run([str(self.launcher), *args], capture_output=True, text=True, env=env, timeout=timeout)
        if check and r.returncode:
            raise AssertionError(f'launcher {args} failed ({r.returncode}): {r.stdout[-2000:]} {r.stderr[-2000:]}')
        return r

    # ---- bundle

    def test_bundle_layout_and_plist(self):
        c = self.app / 'Contents'
        info = plistlib.loads((c / 'Info.plist').read_bytes())
        self.assertEqual(info['CFBundleExecutable'], 'MuNativePreview')
        self.assertEqual(info['CFBundleName'], NAME)
        self.assertEqual(info['CFBundleIdentifier'], 'io.github.fryezero.mu-the-matrix.native-preview')
        self.assertEqual(info['CFBundlePackageType'], 'APPL')
        self.assertEqual(info['CFBundleIconFile'], 'AppIcon')
        self.assertIs(info['MUNativeGFx'], True)
        self.assertEqual((c / 'PkgInfo').read_bytes(), b'APPL????')
        for rel in ('MacOS/MuNativePreview', 'MacOS/mu-client', 'Frameworks/libmu-nonet.dylib',
                    'Frameworks/libmugfx.dylib', 'Resources/AppIcon.icns', 'Resources/session/demo-session.txt',
                    'Resources/session/demo-servers.txt', 'Resources/session/demo-characters.txt',
                    'Resources/world/lorencia-demo-placement.txt', 'Resources/world/lorencia-demo-npc.txt',
                    'Resources/world/lorencia-demo-players.txt',
                    'MacOS/gfxconvert'):
            self.assertTrue((c / rel).is_file(), rel)
        self.assertTrue(os.access(c / 'MacOS/mu-client', os.X_OK))
        # nothing but authored files and built code: no game data, no converted movies, no caches
        names = {p.name for p in self.app.rglob('*')}
        self.assertFalse({n for n in names if n.endswith(('.swf', '.ozg', '.bmd', '.plain', '.tsv', '.pyc', '.py'))})
        self.assertNotIn('__pycache__', names)

    def test_signature_is_adhoc_strict_and_without_hardened_runtime(self):
        r = subprocess.run(['codesign', '--verify', '--strict', '--deep', '--verbose=1', str(self.app)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for f in (self.launcher, self.app / 'Contents/MacOS/mu-client'):
            d = subprocess.run(['codesign', '-dv', '--verbose=2', str(f)], capture_output=True, text=True).stderr
            self.assertIn('Signature=adhoc', d)
            self.assertNotIn('runtime', d.split('flags=')[1].split('\n')[0])

    def test_self_contained_and_no_network_imports(self):
        files = list(macho_files(self.app))
        self.assertGreaterEqual(len(files), 6)
        frameworks = {p.name for p in (self.app / 'Contents/Frameworks').iterdir()}
        for f in files:
            deps = subprocess.run(['otool', '-L', str(f)], capture_output=True, text=True, check=True).stdout
            for line in deps.splitlines()[1:]:
                dep = line.split()[0]
                ok = (dep.startswith(('/System/', '/usr/lib/')) or (dep.startswith('@rpath/') and dep[7:] in frameworks)
                      or dep == f'@rpath/{f.name}')   # a library's own install name
                self.assertTrue(ok, f'{f.name} loads {dep}')
            if f.name == 'libmu-nonet.dylib':
                continue   # the guard itself wraps the socket API
            undefined = set(subprocess.run(['nm', '-u', str(f)], capture_output=True, text=True).stdout.split())
            self.assertFalse(undefined & NETWORK_IMPORTS, f'{f.name} imports {undefined & NETWORK_IMPORTS}')

    def test_check_bundle(self):
        env, _ = self.env('check')
        r = self.launch(env, '--check-bundle')
        self.assertIn('bundle complete', r.stdout)
        self.assertIn('GFx library (Ruffle): bundled', r.stdout)

    def test_network_guard_refuses_sockets_and_lookups(self):
        probe = self.dir / 'probe'
        source = self.dir / 'probe.c'
        source.write_text(r'''
#include <errno.h>
#include <netdb.h>
#include <stdio.h>
#include <sys/socket.h>
int main(void) {
    int a = socket(AF_INET, SOCK_STREAM, 0); int ea = errno;
    int b = socket(AF_INET6, SOCK_DGRAM, 0);
    int u = socket(AF_UNIX, SOCK_STREAM, 0);
    struct addrinfo *r = 0; int g = getaddrinfo("localhost", "80", 0, &r);
    printf("%d %d %d %d %d\n", a, ea, b, u >= 0, g != 0);
    return 0;
}''')
        subprocess.run(['clang', '-o', str(probe), str(source)], check=True, capture_output=True)
        report = self.dir / 'nonet.json'
        env = dict(os.environ, DYLD_INSERT_LIBRARIES=str(self.app / 'Contents/Frameworks/libmu-nonet.dylib'),
                   MU_NONET_REPORT=str(report))
        r = subprocess.run([str(probe)], capture_output=True, text=True, env=env, check=True)
        self.assertEqual(r.stdout.split(), ['-1', '13', '-1', '1', '1'])     # EACCES; AF_UNIX allowed
        self.assertIn('mu-nonet: refused socket(domain) (2)', r.stderr)
        rep = json.loads(report.read_text())
        self.assertEqual((rep['phase'], rep['inet_denied'], rep['lookups_denied'], rep['unix_sockets']), ('exit', 2, 1, 1))
        strict = dict(env, MU_NONET_STRICT='1')
        r = subprocess.run([str(probe)], capture_output=True, text=True, env=strict, check=True)
        self.assertEqual(r.stdout.split()[3], '0')                             # strict: AF_UNIX refused too

    # ---- data setup and plan

    def test_setup_copies_local_data_and_leaves_the_game_folder_alone(self):
        env, base = self.env('setup')
        r = self.launch(env, '--setup')
        nd = base / 'support/Native Data'
        self.assertEqual(sorted(p.name for p in (nd / 'lang').iterdir()), ['notes.txt'])
        self.assertEqual(sorted(p.name for p in (nd / 'objects').iterdir()), ['EncTerrain99.hidden', 'EncTerrain99.plain'])
        self.assertEqual(sorted(p.name for p in (nd / 'gfx').iterdir()), ['Chat.swf', 'base.swf', 'main.swf'])
        self.assertTrue((nd / 'sound/audio-tables.tsv').is_file())
        record = json.loads((nd / 'setup.json').read_text())
        self.assertEqual(record['gfx']['status'], 'copied')
        self.assertIn('no Data/Interface/GFx', record['gfx']['detail'])
        self.assertEqual((record['lang']['files'], record['objects']['files']), (1, 2))
        self.assertIn('gfx: copied', r.stdout)
        # a second run keeps what is there; --force copies again
        self.assertIn('lang: kept', self.launch(env, '--setup').stdout)
        self.assertIn('lang: copied', self.launch(env, '--setup', '--force').stdout)
        self.assertEqual(snapshot(self.root), self.root_before)
        self.assertTrue((base / 'logs/launcher.log').is_file())

    def test_first_run_converter_without_python_or_pillow(self):
        from test_native_gfx import build_root
        import gfxconvert as oracle
        root = write_root(self.dir / 'conversion-root')
        gfx = build_root(root)
        for stem in ('base', 'main'):
            (gfx / f'{stem}.ozg').write_bytes((gfx / 'Test.ozg').read_bytes())
        env, base = self.env('conversion', MU_NATIVE_GAME_ROOT=str(root),
                             MU_NATIVE_SCRATCH=str(self.dir / 'absent-scratch'), PATH='/nonexistent')
        home = base / 'home'
        home.mkdir(parents=True)
        env.update(HOME=str(home), CFFIXED_USER_HOME=str(home))
        # Old settings may carry a python key. It must be ignored, not executed.
        support = base / 'support'
        support.mkdir()
        (support / 'settings.json').write_text(json.dumps({'python': '/must-not-run/python3'}))
        self.launch(env, '--setup')
        nd = support / 'Native Data'
        record = json.loads((nd / 'setup.json').read_text())
        self.assertEqual((record['gfx']['status'], record['gfx']['files']), ('converted', 3))
        fonts = oracle.FontResolver(gfx, 'English', oracle.LATIN_SUBSET)
        for stem in ('Test', 'base', 'main'):
            expected, _ = oracle.convert_movie(gfx / f'{stem}.ozg', fonts, True, bridge=True,
                                               init_vars={'_root.isClient': True})
            self.assertEqual((nd / 'gfx' / f'{stem}.swf').read_bytes(), expected)
        # Repeat and forced replacement both work, also with no Python on PATH.
        self.assertIn('gfx: kept', self.launch(env, '--setup').stdout)
        self.assertIn('gfx: converted', self.launch(env, '--setup', '--force').stdout)
        before = {p.name: p.read_bytes() for p in (nd / 'gfx').glob('*.swf')}
        (gfx / 'Broken.ozg').write_bytes(b'FWS')
        self.launch(env, '--setup', '--force')
        self.assertNotEqual(json.loads((nd / 'setup.json').read_text())['gfx']['status'], 'converted')
        self.assertEqual({p.name: p.read_bytes() for p in (nd / 'gfx').glob('*.swf')}, before)

    def plan(self, env, *args):
        return json.loads(self.launch(env, '--print-plan', *args).stdout)

    def test_plan_defaults_every_feature_on(self):
        env, base = self.env('plan')
        self.launch(env, '--setup')
        p = self.plan(env, '--screen', '1512x945')
        a = p['args']
        self.assertTrue(p['executable'].endswith('Contents/MacOS/mu-client'))
        self.assertEqual(a[a.index('--game-root') + 1], str(self.root))
        for flag in ('--combat', '--items', '--npc'):
            self.assertIn(flag, a)
        for flag in ('--no-names', '--no-env', '--no-particles', '--no-audio'):
            self.assertNotIn(flag, a)
        self.assertEqual(a[a.index('--label') + 1], 'OFFLINE PREVIEW - no server connection')
        self.assertIn('OFFLINE PREVIEW', a[a.index('--title') + 1])
        self.assertIn('no server connection', a[a.index('--title') + 1])
        self.assertEqual((a[a.index('--width') + 1], a[a.index('--height') + 1]), ('1344', '840'))
        nd = base / 'support/Native Data'
        self.assertEqual(a[a.index('--gfx') + 1], str(nd / 'gfx'))
        self.assertEqual(a[a.index('--world-objects') + 1], str(nd / 'objects'))   # EncTerrain99.plain
        self.assertNotIn('--charsel-objects', a)                                  # no EncTerrain94.plain
        self.assertNotIn('--login-objects', a)
        self.assertEqual(a[a.index('--sound-table') + 1], str(nd / 'sound/audio-tables.tsv'))
        self.assertTrue(a[a.index('--npc-demo') + 1].endswith('Resources/world/lorencia-demo-npc.txt'))
        self.assertTrue(a[a.index('--players') + 1].endswith('Resources/world/lorencia-demo-players.txt'))
        self.assertNotIn('--helper', a)                                           # NATIVE-HELPERS-001: none by default
        e = p['env']
        self.assertTrue(e['DYLD_INSERT_LIBRARIES'].endswith('Contents/Frameworks/libmu-nonet.dylib'))
        self.assertTrue(e['MU_GFX_LIB'].endswith('Contents/Frameworks/libmugfx.dylib'))
        self.assertEqual(e['MU_LANG_DIR'], str(nd / 'lang'))
        self.assertTrue(e['MU_NONET_REPORT'].startswith(str(base / 'logs')))
        self.assertEqual(e['MU_EXIT_WITH_PARENT'], '1')   # NATIVE-PERF-001: no client left after a killed launcher
        self.assertNotIn('--fullscreen', a)
        big = self.plan(env, '--screen', '3000x2000')['args']
        self.assertEqual((big[big.index('--width') + 1], big[big.index('--height') + 1]), ('1600', '1000'))

    def test_plan_follows_the_settings(self):
        env, base = self.env('toggles')
        self.launch(env, '--setup')
        settings = {'windowSize': '1024x640', 'gfx': False, 'combat': False, 'items': False, 'names': False,
                    'npc': False, 'env': False, 'particles': False, 'objects': False, 'lang': False, 'sound': False,
                    'players': False, 'helper': 'fenrir-gold'}
        (base / 'support/settings.json').write_text(json.dumps(settings))
        p = self.plan(env)
        a = p['args']
        for flag in ('--no-names', '--no-env', '--no-particles', '--no-audio'):
            self.assertIn(flag, a)
        for flag in ('--combat', '--items', '--npc', '--gfx', '--world-objects', '--sound-table', '--players'):
            self.assertNotIn(flag, a)
        self.assertEqual(a[a.index('--helper') + 1], 'fenrir-gold')
        self.assertNotIn('MU_LANG_DIR', p['env'])
        self.assertNotIn('MU_GFX_LIB', p['env'])
        self.assertEqual((a[a.index('--width') + 1], a[a.index('--height') + 1]), ('1024', '640'))
        self.assertIn('DYLD_INSERT_LIBRARIES', p['env'])                  # the guard is never optional
        out = self.launch(env, '--print-settings').stdout
        self.assertIn('combat: off', out)
        self.assertIn('window size: 1024x640', out)
        settings['windowSize'] = 'full'   # NATIVE-PERF-001: full screen, the fitted size for the window mode
        (base / 'support/settings.json').write_text(json.dumps(settings))
        a = self.plan(env, '--screen', '1512x945')['args']
        self.assertIn('--fullscreen', a)
        self.assertEqual((a[a.index('--width') + 1], a[a.index('--height') + 1]), ('1344', '840'))

    def test_plan_without_movies_falls_back_to_the_stand_ins(self):
        env, base = self.env('nomovies')
        self.launch(env, '--setup')
        shutil.rmtree(base / 'support/Native Data/gfx')
        p = self.plan(env)
        self.assertNotIn('--gfx', p['args'])
        self.assertTrue(any('stand-ins' in n for n in p['notes']))

    # ---- launch

    def test_smoke_runs_the_whole_flow_offline_under_the_guard(self):
        env, base = self.env('smoke')
        r = self.launch(env, '--smoke', '--backend', 'soft', '--frames', '300', '--size', '320x240', check=False)
        result = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])
        self.assertEqual(result['smoke'], 'ok')
        self.assertTrue(result['reached_world'])
        self.assertIn('4 -> 6', ' '.join(result['transitions']))
        n = result['nonet']
        self.assertEqual(n['guard'], 'mu-nonet')
        self.assertEqual(n['phase'], 'exit')
        self.assertEqual((n['inet_denied'], n['other_denied'], n['connects_denied'], n['lookups_denied']), (0, 0, 0, 0))
        log = Path(result['log'])
        self.assertEqual(log.parent, base / 'logs')
        text = log.read_text()
        self.assertIn('--combat', text)
        self.assertIn('{"summary": true', text)
        self.assertTrue((base / 'support/Native Data/setup.json').is_file())   # first run did the setup
        self.assertEqual(snapshot(self.root), self.root_before)


@unittest.skipUnless(MACOS and PRIVATE, 'private: MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PreviewAppPrivate(unittest.TestCase):
    def test_smoke_over_the_installed_game(self):
        app = NATIVE / 'build/app' / f'{NAME}.app'
        subprocess.run(['make', '-C', str(NATIVE), 'preview-app'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if not k.startswith('MU_NATIVE_')}
            env.update(MU_NATIVE_SUPPORT_DIR=f'{tmp}/support', MU_NATIVE_LOG_DIR=f'{tmp}/logs',
                       MU_NATIVE_GAME_ROOT=os.environ['MU_GAME_ROOT'])
            r = subprocess.run([str(app / 'Contents/MacOS/MuNativePreview'), '--smoke', '--backend', 'gl',
                                '--frames', '260'], capture_output=True, text=True, env=env, timeout=900)
            result = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(r.returncode, 0, r.stdout[-3000:])
            self.assertEqual(result['smoke'], 'ok')
            self.assertEqual(result['nonet']['inet_denied'], 0)


if __name__ == '__main__':
    unittest.main()
