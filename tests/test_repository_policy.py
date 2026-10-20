import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('repository_audit',Path(__file__).resolve().parents[1]/'scripts/audit_repository.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PublicationBoundary(unittest.TestCase):
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
