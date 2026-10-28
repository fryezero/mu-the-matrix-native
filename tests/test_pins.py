"""Portable checks of scripts/pins.py, the one home of the validators' pinned inputs (VERIFY-HARNESS-001).

* resolution: explicit path, then the pin's environment variables, then MU_EVIDENCE_DIR (or the
  repository's evidence/); a missing input is PinMissing naming the pin and what moves it, never a
  fallback to another directory;
* identity: size and SHA-256 checks of whole files and of regions, and the shared loader contract;
* the grep test: no digest registered in pins.py is pasted into another script, no script builds its own
  evidence path or falls back to a home-directory copy, and no validator or machine declares a
  module-level input digest of its own.
"""
import ast
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import pins  # noqa: E402

HEX64 = re.compile(r'(?<![0-9a-fA-F])[0-9a-f]{64}(?![0-9a-fA-F])')

# Scripts outside VERIFY-HARNESS-001's ownership that still paste pins. Each is a known debt: migrate it
# (pin and loader lines only) and delete its line here. The test fails for any other file.
UNMIGRATED = {
    'combat_static.py': 'static combat-table extractor; evidence default paths',
    'extract_audio_tables.py': 'audio-table extractor; text/data pins',
    'items_static.py': 'static item-table extractor; evidence default paths',
    'loader_emulate.py': 'protector-loader emulation; main.exe pin and evidence paths',
    'loader_inspect.py': 'protector-loader inspection; evidence path',
    'loader_recover.py': 'protector-loader recovery; main.exe pin',
    'loader_trace_static.py': 'protector-loader trace; evidence path',
    'loader_validate.py': 'protector-loader validation; evidence path',
}
EVIDENCE_PATH = re.compile(r"""main-exe-study|(ROOT|REPO|HERE)\s*/\s*['"]evidence\b|['"]evidence/[\w.-]+/""")
# Module-level digests that pin one client routine's bytes (a one-entry ROUTINES table), not an input.
ROUTINE_CONSTANTS = {'FUNCTION_SHA256'}


def environment(**values):
    """os.environ with the pins' variables cleared and ``values`` set."""
    names = {pins.EVIDENCE_ENV, pins.SNAPSHOT_ENV, pins.MATH_DATA_ENV}
    for pin in pins.PINS.values():
        names.update(pin.env)
    clean = {k: v for k, v in os.environ.items() if k not in names}
    clean.update(values)
    return mock.patch.dict(os.environ, clean, clear=True)


class RegistryTests(unittest.TestCase):
    def test_every_pin_is_well_formed(self):
        for name, pin in pins.PINS.items():
            with self.subTest(pin=name):
                self.assertEqual(pin.name, name)
                self.assertRegex(pin.sha256, r'^[0-9a-f]{64}$')
                self.assertIn(pin.root, {'evidence', 'repo', 'snapshot'})
                self.assertTrue(pin.what)
                if not pin.whole:
                    self.assertIsNotNone(pin.size)
        for name, digest in pins.OTHER_DIGESTS.items():
            self.assertRegex(digest, r'^[0-9a-f]{64}$', name)

    def test_one_identity_per_digest(self):
        """Pins may share a digest (the same bytes at two capture paths) only with the same size."""
        seen = {}
        for pin in pins.PINS.values():
            if pin.sha256 in seen:
                self.assertEqual(seen[pin.sha256].size, pin.size, (seen[pin.sha256].name, pin.name))
                self.assertEqual(seen[pin.sha256].whole, pin.whole)
            seen[pin.sha256] = pin


class ResolutionTests(unittest.TestCase):
    def test_default_is_under_the_evidence_directory(self):
        with environment():
            self.assertEqual(pins.TEXT.default(), ROOT / 'evidence' / 'x86-text-capture-09/client-text.bin')
        with tempfile.TemporaryDirectory() as folder, environment(MU_EVIDENCE_DIR=folder):
            self.assertEqual(pins.DATA.default(), Path(folder) / pins.DATA.relative)

    def test_environment_then_explicit_path_win(self):
        with tempfile.TemporaryDirectory() as folder, environment(MU_EVIDENCE_DIR=folder,
                                                                   MU_CLIENT_IMAGE_DATA='/second'):
            self.assertEqual(pins.DATA.default(), Path('/second'))
            with mock.patch.dict(os.environ, {'MU_IMAGE_DATA': '/first'}):
                self.assertEqual(pins.DATA.default(), Path('/first'))
            self.assertEqual(pins.DATA.path('/given'), Path('/given'))

    def test_missing_input_names_the_pin_and_its_variables(self):
        with tempfile.TemporaryDirectory() as folder, environment(MU_EVIDENCE_DIR=folder):
            with self.assertRaises(pins.PinMissing) as caught:
                pins.TEXT.read()
            message = str(caught.exception)
            self.assertIn("'text'", message)
            self.assertIn('MU_CLIENT_TEXT', message)
            self.assertIn('MU_EVIDENCE_DIR', message)
            self.assertIn(folder, message)
            self.assertIsInstance(caught.exception, FileNotFoundError)
            with self.assertRaises(SystemExit):
                pins.TEXT.read(exit=True)
            self.assertFalse(pins.TEXT.available())

    def test_snapshot_without_a_directory_has_no_location(self):
        with environment():
            self.assertIsNone(pins.LANG3.default())
            with self.assertRaisesRegex(pins.PinMissing, 'no configured location.*MU_SNAPSHOT_DIR'):
                pins.LANG3.path()
        with tempfile.TemporaryDirectory() as folder, environment(MU_SNAPSHOT_DIR=folder):
            self.assertEqual(pins.LANG3.default(), Path(folder) / 'lang/live/lang3.bin')

    def test_math_data_directory(self):
        with tempfile.TemporaryDirectory() as folder, environment(MU_EVIDENCE_DIR=folder):
            self.assertEqual(pins.math_data_dir(), Path(folder) / pins.MATH_DATA_DIR)
            with mock.patch.dict(os.environ, {'MU_MATH_DATA': '/math'}):
                self.assertEqual(pins.math_data_dir(), Path('/math'))
            self.assertEqual(pins.math_data_dir('/given'), Path('/given'))


class IdentityTests(unittest.TestCase):
    def synthetic(self, payload, offset=0, whole=True):
        return pins.Pin('synthetic', hashlib.sha256(payload).hexdigest(), len(payload), None, root='repo',
                        offset=offset, whole=whole, what='synthetic test input')

    def test_whole_file_size_and_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'input.bin'
            path.write_bytes(b'pinned bytes')
            pin = self.synthetic(b'pinned bytes')
            self.assertEqual(pin.read(path), b'pinned bytes')
            path.write_bytes(b'pinned bytes!')
            with self.assertRaises(pins.PinMismatch) as caught:
                pin.read(path)
            self.assertIsInstance(caught.exception, ValueError)
            path.write_bytes(b'pinned bytez')
            with self.assertRaises(pins.PinMismatch):
                pin.read(path)

    def test_region_pin_reads_only_its_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'section.bin'
            path.write_bytes(b'\0' * 100 + b'table' + b'\xff' * 50)
            pin = self.synthetic(b'table', offset=100, whole=False)
            self.assertEqual(pin.read(path), b'table')

    def test_shared_loader_contract(self):
        """pins.load_pinned is the old load_pinned: payload, SystemExit naming the label, and a
        FileNotFoundError (PinMissing) for an absent file."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'text.bin'
            path.write_bytes(b'abc')
            digest = hashlib.sha256(b'abc').hexdigest()
            self.assertEqual(pins.load_pinned(path, 3, digest, 'restored text'), b'abc')
            with self.assertRaisesRegex(SystemExit, r'restored text: unexpected size or SHA-256'):
                pins.load_pinned(path, 4, digest, 'restored text')
            with self.assertRaises(FileNotFoundError):
                pins.load_pinned(Path(folder) / 'absent.bin', 3, digest, 'restored text')
            self.assertEqual(pins.load(path, None, digest), b'abc')
            loader = pins.loader(ValueError, 'Input does not match pinned {label}: {path}')
            with self.assertRaisesRegex(ValueError, f'pinned flag: {re.escape(str(path))}'):
                loader(path, 3, '0' * 64, 'flag')
            self.assertEqual(loader(path, 1, hashlib.sha256(b'b').hexdigest(), 'flag', offset=1), b'b')

    def test_callers_keep_their_promised_errors(self):
        """Inline checks keep the exception their callers and tests expect (and the module constants they
        pass, which tests patch)."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'text.bin'
            path.write_bytes(b'not the text')
            with self.assertRaisesRegex(ValueError, 'pinned restored client text'):
                pins.load(path, pins.TEXT.size, pins.TEXT.sha256,
                          mismatch=ValueError('Capture does not match the pinned restored client text'))
            with self.assertRaisesRegex(SystemExit, 'image data does not match'):
                pins.TEXT.read(path, mismatch=SystemExit('image data does not match the pinned capture'))
            with self.assertRaises(SystemExit):
                pins.TEXT.read(path, exit=True)

    def test_work_dir(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, {'MU_VALIDATOR_WORK': folder}):
            self.assertEqual(pins.work_dir('validate_x'), Path(folder) / 'validate_x')
            self.assertTrue((Path(folder) / 'validate_x').is_dir())


class NoPastedPinsTests(unittest.TestCase):
    """The grep test: pins live only in scripts/pins.py."""

    def scripts(self):
        return sorted(p for p in SCRIPTS.glob('*.py') if p.name != 'pins.py')

    def test_no_registered_digest_outside_pins(self):
        registered = set(pins.digests().values())
        offenders = []
        for path in self.scripts():
            if path.name in UNMIGRATED:
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                for digest in HEX64.findall(line):
                    if digest in registered:
                        offenders.append(f'{path.name}:{number}: {digest[:16]}…')
        self.assertEqual(offenders, [], 'pinned digests pasted outside scripts/pins.py')

    def test_unmigrated_list_is_current(self):
        """Every UNMIGRATED entry still pastes a pin or an evidence path (drop the entry once migrated)."""
        registered = set(pins.digests().values())
        for name in UNMIGRATED:
            text = (SCRIPTS / name).read_text(encoding='utf-8')
            self.assertTrue(registered & set(HEX64.findall(text)) or EVIDENCE_PATH.search(text),
                            f'{name} is migrated: drop it from UNMIGRATED')

    def test_no_private_evidence_paths_outside_pins(self):
        """No script joins its own evidence path or falls back to a home-directory copy of the evidence."""
        offenders = []
        for path in self.scripts():
            if path.name in UNMIGRATED:
                continue
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if EVIDENCE_PATH.search(line):
                    offenders.append(f'{path.name}:{number}: {line.strip()[:100]}')
        self.assertEqual(offenders, [])

    def test_validators_declare_no_input_digest_of_their_own(self):
        """A module-level string constant holding a SHA-256 in a validator or machine is an input pin
        that belongs in pins.py (routine-body constants excepted)."""
        offenders = []
        for path in sorted(SCRIPTS.glob('validate_*.py')) + sorted(SCRIPTS.glob('*_machine.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                names += [e.id for t in node.targets if isinstance(t, ast.Tuple) for e in t.elts
                          if isinstance(e, ast.Name)]
                values = [node.value] + (list(node.value.elts) if isinstance(node.value, ast.Tuple) else [])
                if any(isinstance(v, ast.Constant) and isinstance(v.value, str) and HEX64.fullmatch(v.value)
                       for v in values) and not set(names) <= ROUTINE_CONSTANTS:
                    offenders.append(f'{path.name}:{node.lineno}: {", ".join(names)}')
        self.assertEqual(offenders, [])


if __name__ == '__main__':
    unittest.main()
