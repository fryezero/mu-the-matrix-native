import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('repository_audit',Path(__file__).resolve().parents[1]/'scripts/audit_repository.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PublicationBoundary(unittest.TestCase):
    def test_merge_conflict_markers_are_rejected(self):
        """APP-POLISH-004: a planted marker of each kind is caught; text that only resembles one is not."""
        lt, eq, gt = '<' * 7, '=' * 7, '>' * 7
        for planted in (f'{lt} HEAD\n', f'{eq}\n', f'{eq}\r\n', f'{gt} origin/main\n'):
            with self.subTest(planted=planted):
                content = ('# Status\n\nline one\n' + planted + 'line two\n').encode()
                self.assertIn('merge conflict marker (line 4)', audit.violations('docs/handoff.md', content))
        for clean in (f'x {lt} y\n', f'{eq}=\n', f' {eq}\n', f'{gt}>\n', f'{eq} heading\n', f'{lt}HEAD\n'):
            with self.subTest(clean=clean):
                self.assertEqual(audit.violations('docs/notes.md', clean.encode()), [])
        self.assertEqual(audit.CONFLICT_MARKER_EXEMPT, frozenset())

    def test_tracked_text_files_have_no_merge_conflict_markers(self):
        import subprocess
        root = Path(__file__).resolve().parents[1]
        names = [n for n in subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0') if n]
        found = []
        for name in names:
            path = root / name
            if name in audit.CONFLICT_MARKER_EXEMPT or not path.is_file() or path.is_symlink():
                continue
            content = path.read_bytes()
            if b'\0' not in content and audit.CONFLICT_MARKER.search(content.decode('utf-8', errors='replace')):
                found.append(name)
        self.assertEqual(found, [])

    def test_hotpatch_game_tables_cannot_be_published_as_source(self):
        for name in ('hotpatches.h','inlinesites.h','peepsites.h','orig.h','xform-prologue.h','meshdraw-orig.h'):
            with self.subTest(name=name):
                self.assertTrue(audit.violations('mac-play/hotpatch/'+name,b'/* text table */'))
        for name in ('helper.orig','helper.new'):
            self.assertTrue(audit.violations('mac-play/hotpatch/'+name,b'bytes'))

    def test_readme_media_exception_requires_exact_path_and_bytes(self):
        root = Path(__file__).resolve().parents[1]
        for name in audit.REVIEWED_MEDIA:
            with self.subTest(name=name):
                content = (root / name).read_bytes()
                self.assertEqual(audit.violations(name, content), [])
                self.assertTrue(audit.violations(name, content + b'changed'))
                self.assertTrue(audit.violations('docs/media/unreviewed' + Path(name).suffix, content))

    def test_authored_source_is_allowed(self):
        self.assertEqual(audit.violations('windows-capture/capture-client.c',b'int main(void) { return 0; }'),[])

    def test_local_payload_and_assets_are_rejected(self):
        for name in ['evidence/trace.json','input/main.exe','model-recovery/verified/model.json','assets/model.bmd','runtime/log.txt']:
            with self.subTest(name=name):
                self.assertTrue(audit.violations(name,b'{}'))

    def test_vector_fixture_is_allowed(self):
        self.assertEqual(audit.violations('model-recovery/fixtures/vector.json',b'{"key":"deadbeef"}'),[])

    def test_machine_path_is_rejected(self):
        path='/'+'Users'+'/example/private'
        self.assertTrue(audit.violations('docs/example.md',path.encode()))

    def test_token_pattern_and_binary_content_are_rejected(self):
        self.assertTrue(audit.violations('example.txt',('gh'+'p_'+'x'*40).encode()))
        self.assertTrue(audit.violations('example.txt',b'a\0b'))


if __name__ == '__main__':
    unittest.main()
