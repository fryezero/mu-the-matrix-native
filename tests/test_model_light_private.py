"""Private comparison of the native objects' per-normal light with the client (NATIVE-LIGHT-001,
docs/research/client-model-light.md).

scripts/validate_model_light.py runs the client's bone-track loop, pose builder 0x012b5064 and transform
0x012b5bde in Unicorn for every object the native runtime draws, with RenderObject's arguments from the native
report and the client state read from our own running client (mac-play/diagnostics/lightread), and requires the
per-normal light to equal the native values bit for bit; the pre-NATIVE-LIGHT-001 inputs must differ.
Needs MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, the pinned captures, Unicorn, a local decoded object plaintext
(MU_LIGHT_OBJECTS: EncTerrain<n>.plain) and the snapshot of the same world (MU_LIGHT_SNAPSHOT, with MU_LIGHT_WORLD
the client world index; both local, never committed).
Portable checks: native/tests/test_native_light.py.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'evidence' if (ROOT/'evidence').exists() else Path.home()/'Documents/main-exe-study/evidence'
TEXT = Path(os.environ.get('MU_CLIENT_TEXT', EVIDENCE/'x86-text-capture-09/client-text.bin'))
DATA = Path(os.environ.get('MU_IMAGE_DATA', EVIDENCE/'image-data-run10/data-capture-10/client-image-data.bin'))
FLAG = Path(os.environ.get('MU_TRIG_FLAG', EVIDENCE/'trig-state-15/captures/late/math-dispatch-flag.bin'))
FEATURE = Path(os.environ.get('MU_MATH_DATA', EVIDENCE/'x86-math-capture-09/cpu-features.bin'))
GAME = os.environ.get('MU_GAME_ROOT')
OBJECTS = Path(os.environ.get('MU_LIGHT_OBJECTS', '/nonexistent'))
SNAPSHOT = Path(os.environ.get('MU_LIGHT_SNAPSHOT', '/nonexistent'))
WORLD = os.environ.get('MU_LIGHT_WORLD', '94')


def have_unicorn():
    try:
        import unicorn  # noqa: F401
        return True
    except ImportError:
        return False


class ModelLightPrivateTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and GAME and TEXT.exists() and
                         DATA.exists() and FLAG.exists() and FEATURE.exists() and OBJECTS.exists() and
                         SNAPSHOT.exists() and have_unicorn(),
                         'private captures, game data, a live light snapshot and Unicorn')
    def test_native_object_light_equals_the_client_transform(self):
        subprocess.run(['make', '-C', str(ROOT/'native')], check=True, capture_output=True)
        subprocess.run(['make', '-C', str(ROOT/'reconstructed/model-codec')], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_model_light.py'), '--text', str(TEXT),
                            '--data', str(DATA), '--flag', str(FLAG), '--feature', str(FEATURE), '--game-root', GAME,
                            '--world', WORLD, '--objects', str(OBJECTS), '--live', str(SNAPSHOT),
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        totals = report['totals']
        self.assertEqual(report['live_override'], 1)
        self.assertGreater(totals['objects'], 0)
        self.assertEqual(totals['equal'], totals['normals'])
        self.assertGreater(totals['negative_differ'], 0)


if __name__ == '__main__':
    unittest.main()
