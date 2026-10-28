"""The effects validators consume only the pinned initialized section-3 range."""
from dataclasses import replace
import hashlib
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pins
import validate_effects as effects
import validate_effect_tree as tree


class EffectInputTests(unittest.TestCase):
    def test_validators_reject_changed_or_truncated_range_before_emulation(self):
        payload = b'authored initialized section'
        pin = replace(pins.EFFECTS_INIT, size=len(payload), sha256=hashlib.sha256(payload).hexdigest())
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(pins, 'EFFECTS_INIT', pin):
            path = Path(folder) / 'section.bin'
            args = SimpleNamespace(text=None, data=None, section3=path, sse2_math=1)
            for validator, machine in ((effects, 'Machine'), (tree, 'TreeMachine')):
                with self.subTest(validator=validator.__name__), \
                        mock.patch.object(effects, 'load_pinned', return_value=b''), \
                        mock.patch.object(validator, machine, side_effect=RuntimeError('emulation reached')) as build:
                    for damaged in (payload[:-1], b'X' + payload[1:]):
                        path.write_bytes(damaged)
                        with self.assertRaises(pins.PinMismatch):
                            validator.validate(args)
                    path.unlink()
                    with self.assertRaises(pins.PinMissing):
                        validator.validate(args)
                    build.assert_not_called()
                    for tail in (b'', b'first runtime tail', b'different runtime tail'):
                        path.write_bytes(payload + tail)
                        with self.assertRaisesRegex(RuntimeError, 'emulation reached'):
                            validator.validate(args)
                        self.assertEqual(build.call_args.args[2], payload)

    def test_range_covers_exactly_the_mapped_initialized_bytes(self):
        pin = pins.EFFECTS_INIT
        self.assertFalse(pin.whole)
        self.assertEqual(pin.offset, 0)
        self.assertEqual(pin.base, effects.SEC3_BASE)
        self.assertEqual(pin.size, effects.SEC3_INIT_END - effects.SEC3_BASE)
