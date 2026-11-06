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
from test_native_data_manifest import CLIENT, TEST_PIN, stamp
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
        build = subprocess.run(['make', '-C', str(NATIVE / 'app'), f'B={cls.dir / "build"}', f'MUGFX_LIB={cls.stub}', f'CLIENT_SHA256={TEST_PIN}'],
                               capture_output=True, text=True)
        if build.returncode:
            raise AssertionError('app build failed:\n' + build.stdout[-3000:] + build.stderr[-3000:])
        cls.build_log = build.stdout
        cls.app = cls.dir / 'build' / f'{NAME}.app'
        cls.launcher = cls.app / 'Contents/MacOS/MuNativePreview'
        # a read-only synthetic game folder and a synthetic scratch folder
        cls.root = write_root(cls.dir / 'root')
        (cls.root/'main.exe').write_bytes(CLIENT)
        (cls.dir / 'session').mkdir()
        cls.session = write_session(cls.dir / 'session')                  # synthetic characters (no item files)
        cls.scratch = cls.dir / 'scratch'
        (cls.scratch / 'lang').mkdir(parents=True)
        (cls.scratch / 'lang' / 'notes.txt').write_text('synthetic\n')
        # Native Data producers never write directories/symlinks into a component.
        (cls.scratch / 'lang' / 'tools').mkdir()                      # folders are not copied
        objects = cls.scratch / 'objects/live/plain'
        objects.mkdir(parents=True)
        (objects / 'EncTerrain99.plain').write_bytes(b'\0' * 4)      # a world the flow never enters
        (objects / 'EncTerrain99.hidden').write_text('1\n')
        # Component inventories contain every file the exporter publishes.
        movies = cls.scratch / 'npc/movies'
        movies.mkdir(parents=True)
        for m in ('base', 'main', 'Chat'):
            (movies / f'{m}.swf').write_bytes(b'')                    # names only (the stub library)
        (cls.scratch / 'audio/tables').mkdir(parents=True)
        (cls.scratch / 'audio/tables/audio-tables.tsv').write_text('# synthetic\n')
        cls.manifest_tool = cls.app/'Contents/MacOS/mu-native-data'
        for component in (cls.scratch/'lang', objects, movies, cls.scratch/'audio/tables'):
            stamp(cls.manifest_tool, component, cls.root/'main.exe')
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

    def test_app_build_rebuilds_a_stale_client(self):
        # APP-REFRESH-003: the bundle step asks the client submake even when native/build/mu-client exists.
        dry = subprocess.run(['make', '-n', '-C', str(NATIVE / 'app'), f'B={self.dir / "build"}',
                              f'MUGFX_LIB={self.stub}', f'CLIENT_SHA256={TEST_PIN}'], capture_output=True, text=True)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn('-C .. client', dry.stdout)

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

    def test_guard_stays_active_under_the_documented_nice_command(self):
        """APP-POLISH-004: /usr/bin/nice drops DYLD_* (SIP), so the guard is set by scripts/guarded_run.py,
        which lowers the child's priority itself: `nice -n 10 python scripts/guarded_run.py --guard ... -- prog`."""
        probe = self.dir / 'nice-probe'
        source = self.dir / 'nice-probe.c'
        source.write_text(r'''
#include <errno.h>
#include <stdio.h>
#include <sys/resource.h>
#include <sys/socket.h>
int main(void) {
    int a = socket(AF_INET, SOCK_STREAM, 0); int ea = errno;
    printf("%d %d %d\n", a < 0 ? -1 : 1, a < 0 ? ea : 0, getpriority(PRIO_PROCESS, 0));
    return 0;
}''')
        subprocess.run(['clang', '-o', str(probe), str(source)], check=True, capture_output=True)
        guard = self.app / 'Contents/Frameworks/libmu-nonet.dylib'
        helper = NATIVE.parent / 'scripts/guarded_run.py'
        env = {k: v for k, v in os.environ.items() if not k.startswith('DYLD_') and k != 'MU_NONET_REPORT'}
        report = self.dir / 'nice-guard.json'
        documented = ['/usr/bin/nice', '-n', '10', sys.executable, str(helper), '--guard', str(guard),
                      '--report', str(report), '--', str(probe)]
        base = os.getpriority(os.PRIO_PROCESS, 0)                             # the test may run under nice already
        r = subprocess.run(documented, capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), ['-1', '13', str(min(20, base + 10))])   # refused (EACCES), niced
        rep = json.loads(report.read_text())
        self.assertEqual((rep['guard'], rep['phase'], rep['inet_denied']), ('mu-nonet', 'exit', 1))
        # --nice raises a child's niceness without an outer nice; --strict fails on the refused call
        r = subprocess.run([sys.executable, str(helper), '--guard', str(guard), '--report', str(report),
                            '--nice', '7', '--', str(probe)], capture_output=True, text=True, env=env)
        self.assertEqual((r.returncode, r.stdout.split()[1:]), (0, ['13', str(max(base, 7))]), r.stderr)
        r = subprocess.run([sys.executable, str(helper), '--guard', str(guard), '--report', str(report),
                            '--strict', '--', str(probe)], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 4)
        # a protected launcher between the helper and the program is refused before anything runs
        r = subprocess.run([sys.executable, str(helper), '--guard', str(guard), '--report', str(report),
                            '--', '/usr/bin/nice', '-n', '10', str(probe)], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn('SIP-protected', r.stderr)
        # a program that does not load the guard (hardened runtime: dyld ignores DYLD_*) fails the run
        hardened = self.dir / 'nice-probe-hardened'
        shutil.copy2(probe, hardened)
        subprocess.run(['codesign', '-f', '-s', '-', '-o', 'runtime', str(hardened)], check=True, capture_output=True)
        r = subprocess.run([sys.executable, str(helper), '--guard', str(guard), '--report', str(report),
                            '--', str(hardened)], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(r.stdout.split()[:2], ['1', '0'])
        self.assertIn('did not load', r.stderr)
        # the trap itself: the guard named in front of /usr/bin/nice never loads while SIP is on
        sip = subprocess.run(['csrutil', 'status'], capture_output=True, text=True).stdout
        if 'enabled' in sip:
            report.unlink(missing_ok=True)
            trap = dict(env, DYLD_INSERT_LIBRARIES=str(guard), MU_NONET_REPORT=str(report))
            r = subprocess.run(['/usr/bin/nice', '-n', '10', str(probe)], capture_output=True, text=True, env=trap)
            self.assertEqual(r.stdout.split()[:2], ['1', '0'])                 # the socket was NOT refused
            self.assertFalse(report.exists())

    # ---- data setup and plan

    def test_default_scratch_uses_current_workspace_and_preserves_legacy_fallback(self):
        env, base = self.env('scratch-default')
        home = base / 'home'
        current = home / 'Documents/MTM/mu-mac-tools/native/scratch'
        legacy = home / 'Documents/mu-mac-tools/native/scratch'
        legacy.mkdir(parents=True)
        env.pop('MU_NATIVE_SCRATCH')
        env.update(HOME=str(home), CFFIXED_USER_HOME=str(home))
        self.assertIn(f'scratch: {legacy}', self.launch(env, '--print-settings').stdout)
        current.mkdir(parents=True)
        self.assertIn(f'scratch: {current}\n', self.launch(env, '--print-settings').stdout)
        # NATIVE-DATA-MANIFEST-001: the canonical manifest-bearing export set wins when it exists.
        (current / 'native-data/export').mkdir(parents=True)
        self.assertIn(f'scratch: {current}/native-data/export\n', self.launch(env, '--print-settings').stdout)
        env['MU_NATIVE_SCRATCH'] = str(base / 'explicit')
        self.assertIn(f'scratch: {base / "explicit"}', self.launch(env, '--print-settings').stdout)

    def test_setup_copies_local_data_and_leaves_the_game_folder_alone(self):
        env, base = self.env('setup')
        r = self.launch(env, '--setup')
        nd = base / 'support/Native Data'
        self.assertEqual(sorted(p.name for p in (nd / 'lang').iterdir()), ['native-data.manifest', 'notes.txt'])
        self.assertEqual(sorted(p.name for p in (nd / 'objects').iterdir()), ['EncTerrain99.hidden', 'EncTerrain99.plain', 'native-data.manifest'])
        self.assertEqual(sorted(p.name for p in (nd / 'gfx').iterdir()), ['Chat.swf', 'base.swf', 'main.swf', 'native-data.manifest'])
        self.assertTrue((nd / 'sound/audio-tables.tsv').is_file())
        record = json.loads((nd / 'setup.json').read_text())
        self.assertEqual(record['gfx']['status'], 'copied')
        self.assertIn('no Data/Interface/GFx', record['gfx']['detail'])
        self.assertEqual((record['lang']['files'], record['objects']['files']), (1, 2))
        self.assertIn('gfx: copied', r.stdout)
        # a second run keeps what is there; --force copies again
        self.assertIn('manifest: kept', self.launch(env, '--setup').stdout)
        self.assertIn('lang: copied', self.launch(env, '--setup', '--force').stdout)
        self.assertEqual(snapshot(self.root), self.root_before)
        self.assertTrue((base / 'logs/launcher.log').is_file())

    def test_first_run_converter_without_python_or_pillow(self):
        from test_native_gfx import build_root
        import gfxconvert as oracle
        root = write_root(self.dir / 'conversion-root')
        (root/'main.exe').write_bytes(CLIENT)
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
        self.assertIn('manifest: kept', self.launch(env, '--setup').stdout)
        self.assertIn('gfx: converted', self.launch(env, '--setup', '--force').stdout)
        before = {p.name: p.read_bytes() for p in (nd / 'gfx').glob('*.swf')}
        (gfx / 'Broken.ozg').write_bytes(b'FWS')
        self.launch(env, '--setup', '--force', check=False)
        self.assertNotEqual(json.loads((nd / 'setup.json').read_text())['gfx']['status'], 'converted')
        self.assertEqual({p.name: p.read_bytes() for p in (nd / 'gfx').glob('*.swf')}, before)

    def plan(self, env, *args):
        return json.loads(self.launch(env, '--print-plan', *args).stdout)

    def test_extra_arguments_shell_words(self):
        import shlex
        env, _ = self.env('quoted-args')
        self.launch(env, '--setup')
        samples = [
            "--input-script '/tmp/my journey.txt' --label \"hello world\"",
            "--label '' pre\"mid dle\"post escaped\\ space\tlast\nword",
            r"--label '$HOME $(touch nope); *' \"a\\q\\\"b\"",
            "--label a\\\nb",  # POSIX line continuation
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                expected = shlex.split(sample.replace('\\\n', ''))
                env['MU_NATIVE_EXTRA_ARGS'] = sample
                self.assertEqual(self.plan(env)['args'][-len(expected):], expected)
        for sample in ("'unfinished", '\"unfinished', 'trailing\\'):
            env['MU_NATIVE_EXTRA_ARGS'] = sample
            result = self.launch(env, '--print-plan', check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unfinished quote or escape', result.stderr)

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

    def test_plan_with_missing_movies_refuses_partial_data(self):
        env, base = self.env('nomovies')
        self.launch(env, '--setup')
        shutil.rmtree(base / 'support/Native Data/gfx')
        r = self.launch(env, '--print-plan', check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('Native Data cannot be used:', r.stderr)

    def test_manifest_first_run_and_refusal_under_temporary_home(self):
        env, base = self.env('manifest-home')
        home = base/'home'
        home.mkdir(parents=True)
        env.update(HOME=str(home), CFFIXED_USER_HOME=str(home), PATH='/nonexistent')
        self.launch(env, '--setup')
        nd = base/'support/Native Data'
        manifest = nd/'native-data.manifest'
        self.assertTrue(manifest.is_file())
        text = manifest.read_text()
        self.assertIn('client '+TEST_PIN, text)
        self.assertIn('lang/notes.txt', text)
        manifest.write_text(text.replace(TEST_PIN, '0'*64, 1))
        for args in (('--print-plan',), ('--smoke',), ('--setup', '--force')):
            r = self.launch(env, *args, check=False)
            self.assertEqual(r.returncode, 1)
            self.assertIn('Native Data cannot be used:', r.stderr)
            self.assertIn('Re-acquire Native Data', r.stderr)
        self.assertEqual(manifest.read_text(), text.replace(TEST_PIN, '0'*64, 1))
        self.assertFalse(list((base/'logs').glob('mu-client-*')))

    def test_setup_refuses_unversioned_scratch(self):
        scratch = self.dir/'unversioned'
        (scratch/'lang').mkdir(parents=True)
        (scratch/'lang/notes.txt').write_text('unversioned')
        env, base = self.env('unversioned', MU_NATIVE_SCRATCH=str(scratch))
        r = self.launch(env, '--setup', check=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn('Native Data cannot be used:', r.stdout+r.stderr)
        self.assertFalse((base/'support/Native Data/native-data.manifest').exists())

    def test_setup_imports_a_recorded_mapanim_table_and_refuses_an_unrecorded_one(self):
        # NATIVE-DATA-MANIFEST-001: the lang export's mapanim.tsv (RENDER-WORLDS-AFTER5's object animation rows)
        # reaches Native Data/lang, where the client reads it through MU_LANG_DIR; only when the manifest has it.
        table = '#world\ttype\taction\tspeed\thandler\tparam\textra\n9\t1\t0\t0.5\t2\t0\t2,5,1\n'
        for recorded in (True, False):
            scratch = self.dir / f'mapanim-{recorded}'
            shutil.copytree(self.scratch, scratch)
            lang = scratch / 'lang'
            shutil.rmtree(lang / 'tools')
            if recorded:
                (lang / 'mapanim.tsv').write_text(table)
            stamp(self.manifest_tool, lang, self.root / 'main.exe')
            if not recorded:
                (lang / 'mapanim.tsv').write_text(table)                 # added after the manifest
            env, base = self.env(f'mapanim-{recorded}', MU_NATIVE_SCRATCH=str(scratch))
            r = self.launch(env, '--setup', check=False)
            nd = base / 'support/Native Data'
            if not recorded:
                self.assertEqual(r.returncode, 1)
                self.assertIn('Native Data cannot be used:', r.stdout + r.stderr)
                self.assertFalse((nd / 'native-data.manifest').exists())
                self.assertFalse((nd / 'lang/mapanim.tsv').exists())
                continue
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual((nd / 'lang/mapanim.tsv').read_text(), table)
            self.assertIn(' lang/mapanim.tsv\n', (nd / 'native-data.manifest').read_text())
            check = subprocess.run([str(self.manifest_tool), 'check', str(nd), str(self.root / 'main.exe')],
                                   capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertEqual(self.plan(env)['env']['MU_LANG_DIR'], str(nd / 'lang'))

    # ---- launch

    def test_smoke_runs_the_whole_flow_offline_under_the_guard(self):
        env, base = self.env('smoke', MU_NATIVE_SCRATCH=str(self.dir/'no-smoke-scratch'))
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
            # Without MU_NATIVE_SCRATCH the app takes scratch/native-data/export (NATIVE-DATA-MANIFEST-001,
            # scripts/build_native_data_export.py); MU_NATIVE_SCRATCH still selects another manifest-bearing set.
            env ={k: v for k, v in os.environ.items() if not k.startswith('MU_NATIVE_') or k == 'MU_NATIVE_SCRATCH'}
            env.update(MU_NATIVE_SUPPORT_DIR=f'{tmp}/support', MU_NATIVE_LOG_DIR=f'{tmp}/logs',
                       MU_NATIVE_GAME_ROOT=os.environ['MU_GAME_ROOT'])
            r = subprocess.run([str(app / 'Contents/MacOS/MuNativePreview'), '--smoke', '--backend', 'gl',
                                '--frames', '260'], capture_output=True, text=True, env=env, timeout=900)
            result = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(r.returncode, 0, r.stdout[-3000:])
            self.assertEqual(result['smoke'], 'ok')
            self.assertEqual(result['nonet']['inet_denied'], 0)
            nd = Path(tmp) / 'support/Native Data'
            scratch = Path(json.loads((nd / 'setup.json').read_text())['scratch'])
            if (scratch / 'lang/mapanim.tsv').is_file():                  # AFTER5's rows reach the client's lang
                self.assertEqual((nd / 'lang/mapanim.tsv').read_bytes(), (scratch / 'lang/mapanim.tsv').read_bytes())


if __name__ == '__main__':
    unittest.main()
