"""FOLLOWUPS-001: appearance-only accessories and the GFx frame-zero regression.

The repeatability check needs a libmugfx built with Ruffle patch 0008. The legacy library ignores
MU_GFX_TEST_CLOCK; report that as a precise skip, rather than claim the old runtime is deterministic.
"""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_inventory_fx import SCENE, GFX, InventoryScene, world  # noqa: E402
from test_native_capture_alpha import LorenciaTooltipSceneTests  # noqa: E402
from test_native_gfx2 import assign_fn, RET, tag, swf, conv  # noqa: E402

ACCESSORIES = [(9, 6668), (10, 6664), (11, 6665), (12, 6359), (13, 6601), (14, 6593)]


@unittest.skipUnless(SCENE, 'private: MU_RECOVERY_INTEGRATION, MU_GAME_ROOT, MU_NATIVE_DATA_DIR, MU_GFX_LIB')
class AccessoryFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        InventoryScene.setUpClass()
        cls.exe = InventoryScene.exe

    @classmethod
    def tearDownClass(cls):
        InventoryScene.tearDownClass()

    def test_accessories_are_explicit_and_draw_in_their_slots(self):
        plain, _, _ = world(self.exe)
        self.assertNotIn('inventory_equipment', plain)
        demo, _, _ = world(self.exe, '--gfx-open', 'inventory,equipment-demo')
        self.assertEqual(demo['item_models_missing'], 0)
        self.assertEqual([(e['slot'], e['code']) for e in demo['inventory_equipment']], ACCESSORIES)
        self.assertTrue(all(e['level'] == 0 and e['excellent'] == 0 for e in demo['inventory_equipment']))


def clock_samples():
    """Probe the real AS2 getTimer, without advancing the player between the two readings."""
    lib = ctypes.CDLL(GFX)
    lib.mugfx_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_size_t]
    lib.mugfx_open.restype = ctypes.c_void_p
    for name in ('mugfx_start', 'mugfx_close'):
        getattr(lib, name).argtypes = [ctypes.c_void_p]
    lib.mugfx_invoke.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.mugfx_invoke.restype = ctypes.c_char_p
    with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, MU_GFX_TEST_CLOCK='1'):
        path = Path(tmp)/'clock.swf'
        path.write_bytes(swf([tag(12, assign_fn('_root', 'clock', [], b'\x34' + RET)),
                              tag(12, conv.bridge_actions()), tag(1, b'')], size=(64, 64)))
        error = ctypes.create_string_buffer(512)
        player = lib.mugfx_open(str(path).encode(), 64, 64, error, len(error))
        if not player:
            raise AssertionError(error.value.decode())
        try:
            lib.mugfx_start(player)
            first = lib.mugfx_invoke(player, b'_root', b'clock', b'[]')
            time.sleep(0.05)
            second = lib.mugfx_invoke(player, b'_root', b'clock', b'[]')
            return float(first), float(second)
        finally:
            lib.mugfx_close(player)


@unittest.skipUnless(SCENE, 'private: MU_RECOVERY_INTEGRATION, MU_GAME_ROOT, MU_NATIVE_DATA_DIR, MU_GFX_LIB')
class FrameZero(unittest.TestCase):
    def test_repeated_scene_frame_zero(self):
        first, second = clock_samples()
        if first != 0 or second != 0:
            self.skipTest(f'legacy libmugfx ignores MU_GFX_TEST_CLOCK ({first} -> {second} ms); '
                          'rebuild with patch 0008 before frame-zero repeatability can be verified')
        # Test the actual reported scene, including initial loading, rather than just its isolated timer.
        case = LorenciaTooltipSceneTests()
        with tempfile.TemporaryDirectory() as tmp:
            captures, hashes = [], []
            for i in range(4):
                rows = case.scene('gl', Path(tmp)/str(i))
                captures.append(Path(rows[0]['png']).read_bytes())
                hashes.append(rows[0]['sha256'])
            self.assertEqual(len(set(captures)), 1)
            self.assertEqual(len(set(hashes)), 1)


if __name__ == '__main__':
    unittest.main()
