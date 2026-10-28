"""The effects validators consume only the pinned initialized section-3 range."""
from dataclasses import replace
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pins
import validate_effects as effects
import validate_effect_tree as tree


class EffectInputTests(unittest.TestCase):
    def test_both_validators_use_the_same_range_loader(self):
        self.assertIs(tree.base.load_section3, effects.load_section3)

    def test_range_rejects_changes_and_truncation_but_ignores_unused_tail(self):
        payload = b'authored initialized section'
        pin = replace(pins.EFFECTS_INIT, size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(pins, 'EFFECTS_INIT', pin):
            path = Path(folder) / 'section.bin'
            for tail in (b'', b'first runtime tail', b'different runtime tail'):
                path.write_bytes(payload + tail)
                self.assertEqual(effects.load_section3(path), payload)
            for damaged in (payload[:-1], b'X' + payload[1:]):
                path.write_bytes(damaged)
                with self.assertRaises(pins.PinMismatch):
                    effects.load_section3(path)
            with self.assertRaises(pins.PinMissing):
                effects.load_section3(Path(folder) / 'absent.bin')

    def test_range_covers_exactly_the_mapped_initialized_bytes(self):
        pin = pins.EFFECTS_INIT
        self.assertFalse(pin.whole)
        self.assertEqual(pin.offset, 0)
        self.assertEqual(pin.base, effects.SEC3_BASE)
        self.assertEqual(pin.size, effects.SEC3_INIT_END - effects.SEC3_BASE)
