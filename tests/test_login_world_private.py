"""Private comparisons of the login world (NATIVE-LOGIN-001, docs/research/client-login-scene.md).

1. scripts/validate_login_world.py runs CGMLogInScene_Ex's slots, MoveObject/CreateObject for world 0x5e and
   RenderObjects_AfterCharacter in Unicorn against reconstructed/objects/login_world.c
   (MU_RECOVERY_INTEGRATION=1, the pinned restored text and run10 image data, Unicorn).
2. The live login-screen snapshots (MU_LOGIN_DUMP_DIR with login-a.bin/.globals and login-b.bin/.globals from
   mac-play/diagnostics/objread; decoded game data, local only): creation equals mu_obj_create for every
   object (scripts/live_object_state.py), the camera globals equal the World95 camera record path, and the
   per-step values the handler drives (scroll, PlaySpeed, pulse range, the +0xa flag) advance as reconstructed.
Portable checks: reconstructed/objects/test_login_world.py, reconstructed/scene/test_scene.py.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence' if (ROOT / 'evidence').exists() else Path.home() / 'Documents/main-exe-study/evidence'
TEXT = Path(os.environ.get('MU_CLIENT_TEXT', EVIDENCE / 'x86-text-capture-09/client-text.bin'))
DATA = Path(os.environ.get('MU_IMAGE_DATA', EVIDENCE / 'image-data-run10/data-capture-10/client-image-data.bin'))
DUMPS = Path(os.environ.get('MU_LOGIN_DUMP_DIR', '/nonexistent'))
sys.path.insert(0, str(ROOT / 'scripts'))


def have_unicorn():
    try:
        import unicorn  # noqa: F401
        return True
    except ImportError:
        return False


def read_globals(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'MUGLBLV1'
    out, offset = {}, 8
    while offset < len(data):
        address, size = struct.unpack_from('<II', data, offset)
        out[address] = data[offset + 8:offset + 8 + size]
        offset += 8 + size
    return out


class LoginWorldPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and TEXT.exists() and DATA.exists() and
                         have_unicorn(), 'private pinned client captures and Unicorn')
    def test_routines_match_client(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_login_world.py'), '--text', str(TEXT),
                            '--data', str(DATA), '--cases', '200', '--output', str(output)], check=True,
                           capture_output=True)
            report = json.loads(output.read_text())
        self.assertTrue(report['ok'])
        for name, family in report['families'].items():
            self.assertGreater(family['cases'], 0, name)
            self.assertEqual(family['equal'], family['cases'], name)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and (DUMPS / 'login-a.bin').exists() and
                         (DUMPS / 'login-b.bin').exists(), 'local live login-screen snapshots')
    def test_live_login_screen(self):
        from live_objects_to_plain import read_snapshot
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'live.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/live_object_state.py'), str(DUMPS / 'login-a.bin'),
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())[0]
        self.assertEqual(report['world'], 0x5e)
        self.assertEqual(report['stats']['objects equal'], report['objects'])
        ga, gb = read_globals(DUMPS / 'login-a.globals'), read_globals(DUMPS / 'login-b.globals')
        self.assertEqual(struct.unpack('<3f', ga[0x0bdc58f0]), (-84.5, 0.0, -45.0))          # record angle
        self.assertEqual(struct.unpack('<i', ga[0x01d1df70])[0], 3)
        position = struct.unpack('<3f', ga[0x0bdc5ab4])
        far = struct.unpack('<f', ga[0x01cf1630])[0]
        sys.path.insert(0, str(ROOT / 'native/tests'))
        steps = (struct.unpack('<f', gb[0x06fce370])[0] - struct.unpack('<f', ga[0x06fce370])[0]) / 40.0
        _, _, _, a = read_snapshot(DUMPS / 'login-a.bin')
        _, _, _, b = read_snapshot(DUMPS / 'login-b.bin')
        later = {address: raw for address, _, raw in b}
        f = lambda raw, off: struct.unpack_from('<f', raw, off)[0]
        checked = 0
        for address, _, raw in a:
            t = struct.unpack_from('<i', raw, 0x5c)[0]
            other = later[address]
            if t == 1:      # blend v -= 0.005 per logic step
                self.assertAlmostEqual((f(raw, 0xb0) - f(other, 0xb0)) / 0.005, steps, delta=2.0)
                checked += 1
            if t == 5:      # PlaySpeed 0.23; the ship is an after-character object
                advance = f(other, 0xd0) - f(raw, 0xd0)
                self.assertTrue(abs(advance / 0.23 - steps) < 2.0 or advance < 0, advance)
                self.assertEqual(raw[0xa], 1)
                checked += 1
            if t == 0xd:    # blend light = pulse(0.2, 0.6, ...)
                self.assertTrue(0.2 <= f(raw, 0xa8) <= 0.6)
                self.assertEqual(raw[0xa], 1)
                checked += 1
        self.assertEqual(checked, 4)
        self.assertGreater(far, 0.0)
        self.assertEqual(len(position), 3)


if __name__ == '__main__':
    unittest.main()
