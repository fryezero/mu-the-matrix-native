"""Publication-boundary and consistency tests for mac-play/bundle (MAC-BUNDLE-001, Mu The Matrix.app).

The behavioural tests are the shell suite mac-play/bundle/tests/test-bundle.sh (run by `make test`).
These pin what must stay true of the published tree: authored text only (no app, icon or client bytes),
no personal data or credentials, a well-formed Info.plist template, and documented error codes.
"""
from pathlib import Path
import plistlib
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'mac-play' / 'bundle'
TEXT_SUFFIXES = {'.sh', '.md', '.swift', '.in', '.entitlements', '.txt', ''}


def bundle_files():
    return sorted(p for p in BUNDLE.rglob('*') if p.is_file() and 'build' not in p.relative_to(BUNDLE).parts)


class BundlePublicationBoundary(unittest.TestCase):
    def test_only_authored_text(self):
        files = bundle_files()
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path.name):
                self.assertIn(path.suffix, TEXT_SUFFIXES, 'no app, icon, DLL or other binary may be published')
                data = path.read_bytes()
                self.assertNotIn(b'\0', data)
                self.assertLess(len(data), 64 * 1024)

    def test_no_personal_identifiers_or_credentials(self):
        forbidden = [r'/Users/', r'\bFrye\b', r'mu-the-matrix-dev', r'oliverah5', r'@gmail\.', r'find-generic-password',
                     r'security\s', r'ghp_', r'github_pat_', r'PRIVATE KEY', r'(?i)\bpassword\b', r'mu-mac-tools']
        for path in bundle_files():
            text = path.read_text(encoding='utf-8', errors='replace')
            for pattern in forbidden:
                with self.subTest(path=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text), f'{path.name} matches {pattern}')

    def test_dmg_tooling_is_text_and_entitlements_are_plists(self):
        # MAC-DMG-001: the disk image is generated at build time (no committed background or .DS_Store).
        tracked = subprocess.run(['git', 'ls-files', 'mac-play/bundle'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split('\n')
        self.assertFalse([n for n in tracked if n.endswith(('.dmg', '.tiff', '.DS_Store', '.tar.xz'))])
        for name in ('app.entitlements', 'helpers.entitlements'):
            with self.subTest(name=name):
                plist = plistlib.loads((BUNDLE / 'dmg' / name).read_bytes())
                self.assertIsInstance(plist, dict)
                self.assertTrue(all(k.startswith('com.apple.security.cs.') for k in plist))

    def test_build_output_is_ignored_and_untracked(self):
        self.assertIn('/mac-play/bundle/build/', (ROOT / '.gitignore').read_text())
        tracked = subprocess.run(['git', 'ls-files', 'mac-play/bundle'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split('\n')
        self.assertFalse([n for n in tracked if '/build/' in n or n.endswith(('.app', '.icns', '.png', '.dll', '.exe'))])


class BundleConsistency(unittest.TestCase):
    def test_info_plist_template(self):
        text = (BUNDLE / 'Info.plist.in').read_text()
        fields = set(re.findall(r'@([A-Z_0-9]+)@', text))
        self.assertEqual(fields, {'BUNDLE_ID', 'VERSION', 'BUILD', 'MIN_MACOS', 'DEFAULT_RUNTIME', 'DEFAULT_BOTTLE', 'DEFAULT_FAST_X87', 'DEFAULT_TIMEWALKER_DIR'})
        makefile = (BUNDLE / 'Makefile').read_text()
        for field in fields:
            self.assertIn(f'@{field}@', makefile, f'Makefile must substitute {field}')
        values = {'BUNDLE_ID': 'x.y', 'VERSION': '1.0', 'BUILD': '1', 'MIN_MACOS': '13.0', 'DEFAULT_RUNTIME': 'free', 'DEFAULT_BOTTLE': 'B',
                  'DEFAULT_FAST_X87': 'false', 'DEFAULT_TIMEWALKER_DIR': ''}
        plist = plistlib.loads(re.sub(r'@([A-Z_0-9]+)@', lambda m: values[m.group(1)], text).encode())
        self.assertEqual(plist['CFBundleExecutable'], 'MuTheMatrix')
        self.assertEqual(plist['CFBundlePackageType'], 'APPL')
        self.assertEqual(plist['CFBundleIconFile'], 'AppIcon')
        self.assertIs(plist['MUDefaultFastX87'], False)

    def test_error_codes_match_app_and_readme(self):
        script = (BUNDLE / 'mu-launch.sh').read_text()
        swift = (BUNDLE / 'Sources' / 'Core.swift').read_text()
        readme = (BUNDLE / 'README.md').read_text()
        used = {int(c) for c in re.findall(r'\bfail (\d+) ', script)}
        self.assertEqual(used, {2, 10, 11, 12, 13, 14, 15, 16, 17, 20, 30, 31})
        for code in used - {2}:
            with self.subTest(code=code):
                self.assertRegex(swift, rf'case {code}: return "')
                self.assertRegex(readme, rf'\n\| {code} \| ')

    def test_settings_keys_documented(self):
        swift = (BUNDLE / 'Sources' / 'Core.swift').read_text()
        readme = (BUNDLE / 'README.md').read_text()
        keys = re.search(r'static let keys = \[([^\]]*)\]', swift).group(1)
        for key in re.findall(r'"(\w+)"', keys):
            with self.subTest(key=key):
                self.assertIn(f'`{key}`', readme)

    def test_hooked_into_make(self):
        makefile = (ROOT / 'Makefile').read_text()
        self.assertIn('bash mac-play/bundle/tests/test-bundle.sh', makefile)
        self.assertIn('mac-bundle:', makefile)
        self.assertIn('player-app:\n\t$(MAKE) -C mac-play/bundle player-app', makefile)

    def test_player_app_requires_the_pinned_files(self):
        # MAC-APP-002: an app without mugl, the mscoree proxy and fast x87 installs a ~4 fps game whose final check
        # fails, so the player build refuses to build without them and verifies the result.
        makefile = (BUNDLE / 'Makefile').read_text()
        target = makefile[makefile.index('\nplayer-app:'):]
        target = target[:target.index('\n\n')]
        for var in ('EMBED_MUGL', 'EMBED_MSCOREE', 'EMBED_FAST_X87'):
            with self.subTest(var=var):
                self.assertIn(f'if [ -z "$({var})" ]', target)
        self.assertIn('exit 1', target)
        self.assertIn('--check-bundle', target)
        swift = (BUNDLE / 'Sources' / 'main.swift').read_text()
        self.assertIn('case "--check-bundle":', swift)
        self.assertIn('This copy of Mu The Matrix is incomplete', swift)


if __name__ == '__main__':
    unittest.main()
