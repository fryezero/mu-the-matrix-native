"""Publication-boundary and consistency tests for mac-play/installer (MAC-KIT-001).

The behavioural tests are the shell suite mac-play/installer/tests/test-mukit.sh (run by `make test`).
These tests pin what must stay true of the published tree: no personal data, credentials or binaries,
SHA-256 pins documented and well formed, every option documented.
"""
import os
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'mac-play' / 'installer'
TEXT_SUFFIXES = {'.sh', '.md', '.reg', '.if', '.conf'}


def kit_files():
    return sorted(p for p in KIT.rglob('*') if p.is_file() and 'build' not in p.relative_to(KIT).parts)


class InstallerPublicationBoundary(unittest.TestCase):
    def test_only_authored_text_and_synthetic_fixtures(self):
        files = kit_files()
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.name):
                self.assertIn(path.suffix, TEXT_SUFFIXES, 'no DLL, EXE or other binary may be published')
                data = path.read_bytes()
                self.assertNotIn(b'\0', data)
                self.assertLess(len(data), 128 * 1024)
                if path.suffix == '.sh':
                    self.assertTrue(os.access(path, os.X_OK) or path.parent.name == 'lib', f'{path.name} should be executable')

    def test_no_personal_identifiers_machine_paths_or_credentials(self):
        # The owner's account ID, Keychain item and machine paths must be parameters, not constants.
        forbidden = [r'/Users/', r'\bFrye\b', r'mu-the-matrix-dev', r'oliverah5', r'@gmail\.', r'find-generic-password',
                     r'add-generic-password', r'ghp_', r'github_pat_', r'PRIVATE KEY', r'(?i)\bpassword\s*=', r'mu-mac-tools']
        for path in kit_files():
            text = path.read_text(encoding='utf-8', errors='replace')
            for pattern in forbidden:
                with self.subTest(path=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text), f'{path.name} matches {pattern}')

    def test_fixtures_are_synthetic(self):
        fixtures = {p.name: p.read_bytes() for p in (KIT / 'tests' / 'fixtures').iterdir()}
        self.assertEqual(fixtures['LauncherOption.live.if'], b'DevModeIndex:4\r\nWindowMode:1\r\nID:Player')
        for name, data in fixtures.items():
            self.assertLess(len(data), 2048, name)
        # CRLF fixtures must survive git's text=auto normalisation.
        attributes = (ROOT / '.gitattributes').read_text()
        self.assertIn('/mac-play/installer/tests/fixtures/* -text', attributes)
        self.assertIn('/mac-play/installer/build/', (ROOT / '.gitignore').read_text())

    def test_build_cache_is_ignored_and_untracked(self):
        tracked = subprocess.run(['git', 'ls-files', 'mac-play/installer'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
        self.assertFalse([name for name in tracked if '/build/' in name or name.endswith(('.dll', '.exe'))])


class InstallerPinsAndOptions(unittest.TestCase):
    def setUp(self):
        self.lib = (KIT / 'lib' / 'mukit.sh').read_text()
        self.readme = (KIT / 'README.md').read_text()
        self.setup = (KIT / 'setup-mu-mac.sh').read_text()

    def pins(self):
        return dict(re.findall(r'^(MUKIT_[A-Z0-9_]+_SHA256)=\$\{[A-Z0-9_]+:-([0-9a-f]{64})\}$', self.lib, re.M))

    def test_pins_are_well_formed_documented_and_overridable_only_by_name(self):
        pins = self.pins()
        self.assertEqual(set(pins), {'MUKIT_MAIN_EXE_SHA256', 'MUKIT_LAUNCHER_EXE_SHA256', 'MUKIT_MUGL_V76_SHA256', 'MUKIT_MUGL_V75_SHA256', 'MUKIT_MUGL_V72_SHA256',
                                     'MUKIT_MUGL_V71_SHA256', 'MUKIT_MUGL_V70_SHA256', 'MUKIT_MSCOREE_PROXY_SHA256',
                                     'MUKIT_DOTNET48_INSTALLER_SHA256', 'MUKIT_RT_CX24_ENGINE_SHA256', 'MUKIT_RT_TEMPLATE_SHA256',
                                     'MUKIT_WINETRICKS_SHA256'})
        self.assertEqual(len(set(pins.values())), len(pins))
        for name, digest in pins.items():
            with self.subTest(pin=name):
                self.assertIn(digest, self.readme, 'every pin must be listed in the README hash table')
        # the client identity pin is the repository's pinned target
        self.assertEqual(pins['MUKIT_MAIN_EXE_SHA256'], '3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a')
        self.assertIn('MUKIT_CX263_OPENGL32_SHA256=0965d21be959f804d0dedaa4a52da952befbc9b73df573229c0074390823ec56', self.lib)

    def test_every_setup_option_is_documented(self):
        usage = self.setup[self.setup.index("usage() {"):self.setup.index("\nEOF\n}", self.setup.index("usage() {"))]
        options = set(re.findall(r'^\s+(--[a-z0-9-]+)', usage, re.M))
        self.assertGreaterEqual(len(options), 20)
        for option in options:
            with self.subTest(option=option):
                self.assertIn(option, self.readme)
                self.assertIn(f'{option})', self.setup, 'usage text lists an option the parser does not accept')

    def test_prebuilt_and_private_binaries_never_come_from_the_repository(self):
        self.assertIn('--dll-dir', self.setup)
        self.assertRegex(self.setup, r"MUGL_SRC=\"\$DLL_DIR/mugl-\$MUGL_VERSION\.dll\"")
        self.assertIn('does not match the pinned', self.setup)
        self.assertIn('Do not commit or redistribute it', self.setup)
        self.assertIn('never be committed to the repository or uploaded as a CI artifact', self.readme)
        # the default is the public batching-only build from repository sources
        self.assertIn('DLL_SOURCE=build', self.setup)
        self.assertIn('MUGL_BUILD=public', self.setup)

    def test_protected_bottles_match_the_existing_setup(self):
        existing = (ROOT / 'mac-play' / 'setup-crossover-32bit.sh').read_text()
        for name in ('mumatrix32', 'windows10mu', 'steam', 'mumatrixrecovery'):
            with self.subTest(name=name):
                self.assertIn(name, self.lib)
                self.assertIn(name, existing)

    def test_free_runtime_downloads_are_pinned_https(self):
        # The free runtime is fetched over https and checked against pinned SHA-256 values (MAC-FREE-001).
        for name in ('MUKIT_RT_CX24_ENGINE_URL', 'MUKIT_RT_TEMPLATE_URL', 'MUKIT_WINETRICKS_URL', 'MUKIT_GAME_INSTALLER_URL'):
            with self.subTest(url=name):
                m = re.search(rf'^{name}=\$\{{{name}:-(\S+)\}}$', self.lib, re.M)
                self.assertIsNotNone(m)
                self.assertTrue(m.group(1).startswith('https://'))
        self.assertIn('MUKIT_RT_ARCHIVE_URL=${MUKIT_RT_ARCHIVE_URL:-}', self.lib)
        build = (KIT / 'runtime' / 'build-wine.sh').read_text()
        self.assertIn('crossover-sources-26.3.0.tar.gz', build)
        self.assertRegex(build, r'CX_SRC_SHA256=[0-9a-f]{64}')
        self.assertIn('SOURCES.txt', build)

    def test_relation_to_existing_setup_is_documented(self):
        self.assertIn('Relation to `setup-crossover-32bit.sh`', self.readme)
        self.assertIn('It was itself run live on 2026-10-17 in a throwaway bottle', self.readme)
        self.assertIn('Live validation of the repository version', self.readme)
        self.assertIn('(no login;', self.readme)
        mac_play = (ROOT / 'mac-play' / 'README.md').read_text()
        self.assertIn('installer/README.md', mac_play)


if __name__ == '__main__':
    unittest.main()
