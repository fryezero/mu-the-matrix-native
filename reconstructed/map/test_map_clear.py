"""What a numbered teleport clears (PLAY-FIX-001): portable checks of reconstructed/map/map_clear.c.

The client comparison is scripts/validate_teleport_clear.py (private, Unicorn); these synthetic cases pin the
same rules without client bytes."""
import ctypes
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_teleport_clear as vt  # noqa: E402


class TeleportClearTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.L = vt.Native().L

    def clears(self, number, world, current):
        t = vt.vm_teleport()(number, world, 1, 2, 3)
        out = (ctypes.c_int32 * 5)()
        return list(out[:self.L.mu_teleport_clears(ctypes.byref(t), current, out)])

    def test_order(self):
        self.assertEqual(self.clears(0, 3, 0), [])
        self.assertEqual(self.clears(7, 0, 0), [1, 2, 3])
        self.assertEqual(self.clears(7, 3, 0), [1, 2, 3, 4, 5])

    def test_plates_hidden(self):
        hidden = [w for w in range(-5, 300) if self.L.mu_map_plates_hidden(w)]
        self.assertEqual(hidden, [18, 19, 20, 21, 22, 23, 53, 97])

    def run_clear(self, keys, live, key, scene, world, hero_key, owned=()):
        slots = (vt.Slot * len(keys))(*[vt.Slot(l, k) for k, l in zip(keys, live)])
        own = (vt.Owned * max(len(owned), 1))(*[vt.Owned(l, o) for l, o in owned])
        events = (vt.Event * 512)()
        n = self.L.mu_map_clear_characters(slots, len(keys), own, len(owned), key, scene, world, hero_key, events, 512)
        return [(e.kind, e.slot, e.index) for e in events[:n]], [s.live for s in slots], [o.live for o in own][:len(owned)]

    def test_everyone_but_the_hero(self):
        # the hero (0x1234) stays; two monsters are killed and lose their plates; a dead slot is only reset
        events, live, _ = self.run_clear([0x1234, 0x100, 0x101, 0x102], [1, 1, 1, 0], 0x1234, 6, 0, 0x1234)
        self.assertEqual(live, [1, 0, 0, 0])
        removed = [s for k, s, _ in events if k == vt.REMOVE]
        self.assertEqual(removed, [1, 2])
        self.assertEqual([s for k, s, _ in events if k == vt.RESET], [0, 1, 2, 3])
        self.assertEqual(events[1:6], [(vt.KILL, 1, 0), (vt.REMOVE, 1, 0), (vt.RELEASE, 1, 0), (vt.DETACH, 1, 0),
                                       (vt.RESET, 1, 0)])

    def test_no_plate_calls_outside_the_world_or_in_chaos_castle(self):
        for scene, world in ((5, 0), (6, 18), (6, 97)):
            events, live, _ = self.run_clear([1, 2], [1, 1], 1, scene, world, 1)
            self.assertEqual(live, [1, 0])
            self.assertNotIn(vt.REMOVE, [k for k, _, _ in events], (scene, world))

    def test_signed_key_and_owned_objects(self):
        events, live, owned = self.run_clear([-5, 9], [1, 1], -5, 6, 0, -5, owned=[(1, 1), (1, 0), (0, 1), (1, -1)])
        self.assertEqual(live, [1, 0])
        self.assertEqual(owned, [0, 1, 0, 1])
        self.assertIn((vt.OWN, 1, 0), events)

    def test_clear_items(self):
        for handler, a, b, invoked in ((0, 0, 0, 0), (1, 1, 1, 0), (1, 0, 1, 1), (1, 1, 0, 1), (1, 0, 0, 1)):
            items = (ctypes.c_uint8 * 4)(1, 0, 1, 1)
            self.assertEqual(self.L.mu_map_clear_items(handler, a, b, items, 4), invoked)
            self.assertEqual(list(items), [0, 0, 0, 0])


if __name__ == '__main__':
    unittest.main()
