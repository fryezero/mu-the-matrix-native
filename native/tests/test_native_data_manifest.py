"""Portable provenance/integrity checks, entirely authored inputs."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys

NATIVE = Path(__file__).resolve().parents[1]
PIN = '3cf91f3c203d305a771b04d00b271871f7ce1c6779b22e30fbae8c4f35b5527a'
CLIENT = b'authored synthetic client build\n'
TEST_PIN = hashlib.sha256(CLIENT).hexdigest()


def compile_tool(output, source=None):
    prefix = subprocess.check_output(['brew', '--prefix', 'cryptopp'], text=True).strip() if shutil.which('brew') else '/usr'
    subprocess.run(['clang++', '-std=c++17', '-O1', '-Wall', '-Wextra', '-Werror', '-DMU_MANIFEST_TOOL',
                    f'-DMU_CLIENT_SHA256="{TEST_PIN}"', '-isystem', prefix + '/include',
                    '-I', str(NATIVE/'data'), str(source or NATIVE/'data/manifest.cpp'),
                    '-L'+prefix+'/lib', '-lcryptopp', '-o', str(output)], check=True, capture_output=True)


def stamp(tool, directory, client, *sources):
    subprocess.run([str(tool), 'write', str(directory), str(client), 'synthetic-test-v1',
                    *map(str, sources or [client])], check=True, capture_output=True)


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tool = Path(cls.tmp.name)/'mu-native-data'
        compile_tool(cls.tool)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.base = Path(self.folder.name)
        self.client = self.base/'main.exe'
        self.client.write_bytes(CLIENT)
        self.data = self.base/'Native Data'
        self.data.mkdir()
        (self.data/'table.txt').write_text('authored\n')
        stamp(self.tool, self.data, self.client)
        self.manifest = self.data/'native-data.manifest'

    def check(self, ok=True, tool=None):
        r = subprocess.run([str(tool or self.tool), 'check', str(self.data), str(self.client)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0 if ok else 1, r.stderr)
        if not ok:
            self.assertIn('Native Data cannot be used:', r.stderr)
            self.assertIn('Re-acquire Native Data', r.stderr)
        return r

    def test_match_and_input_provenance(self):
        self.check()
        self.assertIn(f'client {TEST_PIN}', self.manifest.read_text())
        self.assertIn(f'input {TEST_PIN} {len(CLIENT)} 0/0/main.exe', self.manifest.read_text())
        stamp(self.tool, self.data, self.client)
        self.check()


    def test_production_pin_matches_evidence_index_and_app(self):
        evidence = json.loads((NATIVE.parent/'docs/evidence-index.json').read_text())
        self.assertEqual(evidence['target']['sha256'], PIN)
        self.assertIn(PIN, (NATIVE/'data/manifest.cpp').read_text())
        self.assertIn(PIN, (NATIVE/'app/Makefile').read_text())

    def test_lang_export_writes_provenance_and_rejects_dirty_destination(self):
        sys.path.insert(0, str(NATIVE.parent/'scripts'))
        import native_data_manifest as manifest
        import live_lang_to_plain as lang
        from test_native_lang import synthetic_snapshot
        source = self.base/'snapshot'
        source.write_bytes(synthetic_snapshot())
        output = self.base/'exported-lang'
        with patch.object(manifest, 'TOOL', self.tool):
            self.assertEqual(lang.main([str(source), '--out', str(output), '--main-exe', str(self.client)]), 0)
            text = (output/'native-data.manifest').read_text()
            self.assertIn(hashlib.sha256(source.read_bytes()).hexdigest(), text)
            (output/'globaltext.txt').write_text('tampered')
            with self.assertRaises(SystemExit):
                lang.main([str(source), '--out', str(output), '--main-exe', str(self.client)])

    def test_mismatch_build_and_installed_client(self):
        self.manifest.write_text(self.manifest.read_text().replace(TEST_PIN, '0'*64, 1))
        self.check(False)
        self.manifest.unlink()
        stamp(self.tool, self.data, self.client)
        self.client.write_bytes(b'new build')
        self.check(False)

    def test_missing_and_partial(self):
        text = self.manifest.read_text()
        self.manifest.unlink()
        self.check(False)
        for partial in ('', text[:30], text.rsplit('complete ', 1)[0], text+'extra\n'):
            self.manifest.write_text(partial)
            self.check(False)

    def test_missing_added_and_tampered_output(self):
        p = self.data/'table.txt'
        p.write_text('modified\n')
        self.check(False)
        p.unlink()
        self.check(False)
        p.write_text('authored\n')
        (self.data/'extra.txt').write_text('unrecorded')
        self.check(False)

    def test_tampered_entry_duplicate_path_and_traversal(self):
        text = self.manifest.read_text()
        row = next(r for r in text.splitlines() if r.startswith('file '))
        for bad in (text.replace(row.split()[1], '0'*64), text.replace('complete 1', row+'\ncomplete 1'),
                    text.replace('table.txt', '../outside.txt'), text.replace('complete 1', 'complete 2')):
            self.manifest.write_text(bad)
            self.check(False)

    def test_symlink_refused(self):
        p = self.data/'table.txt'
        p.unlink()
        p.symlink_to(self.client)
        self.check(False)

    def test_writer_refuses_wrong_build_and_missing_source(self):
        before = self.manifest.read_bytes()
        for client, source in ((self.client, self.base/'absent'), (self.base/'absent', self.client)):
            r = subprocess.run([str(self.tool), 'write', str(self.data), str(client), 'test', str(source)], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(self.manifest.read_bytes(), before)

    def test_native_consumer_refuses_managed_missing_mismatch_and_tamper(self):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-lang'], check=True, capture_output=True)
        # Independent authored manifest with the production build pin.
        self.manifest.write_text(self.manifest.read_text().replace(TEST_PIN, PIN, 1))
        for corruption in ('mismatch', 'tamper', 'missing'):
            text = self.manifest.read_text()
            if corruption == 'mismatch': self.manifest.write_text(text.replace(PIN, '0'*64, 1))
            if corruption == 'tamper': (self.data/'table.txt').write_text('changed')
            if corruption == 'missing': self.manifest.unlink()
            r = subprocess.run([str(NATIVE/'build/mu-lang'), str(self.data), 'summary'], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('Native Data cannot be used:', r.stderr)
            self.manifest.write_text(text)
            (self.data/'table.txt').write_text('authored\n')

    def test_native_consumer_does_not_treat_display_text_as_a_path(self):
        from test_native_shell import write_root
        root = write_root(self.base/'root')
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-shell'], check=True, capture_output=True)
        result = subprocess.run([str(NATIVE/'build/mu-shell'), '--game-root', str(root),
                                 '--headless', '--frames', '1', '--label', 'Native Data',
                                 '--title', 'Native Data', '--no-audio', '--quiet'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_planted_mistakes_are_caught(self):
        original = (NATIVE/'data/manifest.cpp').read_text()
        mutations = {
            'build': ('m.build == MU_CLIENT_SHA256', 'true'),
            'inventory': ('inventory(dir) == m.files', 'true'),
            'completion': ('end && !std::getline(f, line)', '!std::getline(f, line)'),
        }
        text = self.manifest.read_text()
        for name, (old, new) in mutations.items():
            source = self.base/(name+'.cpp')
            source.write_text(original.replace(old, new, 1).replace('bool end = false;', '[[maybe_unused]] bool end = false;'))
            binary = self.base/name
            compile_tool(binary, source)
            if name == 'build': self.manifest.write_text(text.replace(TEST_PIN, '0'*64, 1))
            if name == 'inventory': (self.data/'table.txt').write_text('tampered')
            if name == 'completion': self.manifest.write_text(text.rsplit('complete ', 1)[0])
            result = subprocess.run([str(binary), 'check', str(self.data)], capture_output=True)
            self.assertEqual(result.returncode, 0, name)  # planted bug wrongly accepts the invalid set
            self.check(False)
            self.manifest.write_text(text)
            (self.data/'table.txt').write_text('authored\n')


if __name__ == '__main__':
    unittest.main()
