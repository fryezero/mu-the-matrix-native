import io
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from recover_images import decode, unwrap


class RecoveryTests(unittest.TestCase):
    def test_conventional_formats_round_trip(self):
        for ext, fmt, prefix in [('.ozj', 'JPEG', 24), ('.ozt', 'TGA', 4), ('.ozb', 'BMP', 4), ('.ozp', 'PNG', 4)]:
            with self.subTest(ext=ext), tempfile.TemporaryDirectory() as tmp:
                buf = io.BytesIO()
                Image.new('RGB', (7, 5), (27, 80, 140)).save(buf, format=fmt)
                raw = buf.getvalue()
                path = Path(tmp) / ('fixture' + ext)
                path.write_bytes(raw[:prefix] + raw)
                decoded, facts = decode(path)
                self.assertEqual(decoded.size, (7, 5))
                self.assertEqual(facts['format'], fmt)
                self.assertEqual(path.read_bytes(), raw[:prefix] + raw)

    def test_custom_tga_wrapper_preserves_alpha(self):
        buf = io.BytesIO()
        Image.new('RGBA', (7, 5), (27, 80, 140, 90)).save(buf, format='TGA')
        raw = buf.getvalue()
        payload, _, fmt = unwrap(raw[:4] + bytes(4) + raw[4:], '.ozt')
        self.assertEqual(payload, raw)
        self.assertEqual(fmt, 'TGA')

    def test_tga_payload_in_ozj(self):
        buf = io.BytesIO()
        Image.new('RGBA', (7, 5), (27, 80, 140, 90)).save(buf, format='TGA')
        raw = buf.getvalue()
        payload, _, fmt = unwrap(raw[:24] + raw, '.ozj')
        self.assertEqual(payload, raw)
        self.assertEqual(fmt, 'TGA')

    def test_unknown_and_text_payloads_rejected(self):
        for ext in ['.ozj', '.ozt', '.ozb', '.ozp', '.bmd']:
            with self.subTest(ext=ext), self.assertRaises(ValueError):
                unwrap(b'version 1\nnodes\n' * 4, ext)

    def test_truncated_image_rejected(self):
        buf = io.BytesIO()
        Image.new('RGB', (20, 20)).save(buf, format='PNG')
        raw = buf.getvalue()[:40]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'broken.ozp'
            path.write_bytes(raw[:4] + raw)
            with self.assertRaises(Exception):
                decode(path)

    def test_bmp_size_mismatch_rejected(self):
        buf = io.BytesIO()
        Image.new('RGB', (7, 5)).save(buf, format='BMP')
        raw = buf.getvalue()
        with self.assertRaises(ValueError):
            unwrap(raw[:4] + raw + b'extra', '.ozb')


if __name__ == '__main__':
    unittest.main()
