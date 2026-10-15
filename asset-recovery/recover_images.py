#!/usr/bin/env python3
"""Read-only MU image-wrapper recovery, derived from local byte evidence.

This is a limited asset utility, not a reconstructed game client.
Original files are never written. Requires Pillow >= 11.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import warnings
from PIL import Image

SUPPORTED = {'.ozj', '.ozt', '.ozb', '.ozp'}


def unwrap(data, extension):
    """Return complete conventional image bytes and observed wrapper layout."""
    if extension == '.ozj':
        if data[24:27] == b'\xff\xd8\xff':
            return data[24:], '24-byte prefix removed', 'JPEG'
        # Eight locally observed files use the OZJ wrapper around TGA pixels.
        if data[:24] == data[24:48] and data[24:27] == b'\x00\x00\x02':
            return data[24:], '24-byte prefix removed; TGA payload in OZJ', 'TGA'
        raise ValueError('No supported image signature at observed offset 24')
    if extension == '.ozb':
        if data[:4] != data[4:8] or data[4:6] != b'BM':
            raise ValueError('Not an observed duplicated-prefix BMP wrapper')
        payload = data[4:]
        if len(payload) < 54 or struct.unpack_from('<I', payload, 2)[0] != len(payload):
            raise ValueError('BMP declared length mismatch')
        return payload, 'duplicated 4-byte prefix removed', 'BMP'
    if extension == '.ozp':
        if data[:4] != data[4:8] or data[4:12] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Not an observed duplicated-prefix PNG wrapper')
        return data[4:], 'duplicated 4-byte prefix removed', 'PNG'
    if extension == '.ozt':
        # Most wrappers repeat bytes 0..3 at 4..7. Fourteen local custom
        # images instead have zeros at 4..7, retaining type information at 2.
        # Both observed layouts reconstruct by dropping only bytes 4..7.
        if len(data) < 22 or (data[4:8] != data[:4] and data[4:8] != b'\0'*4):
            raise ValueError('Unrecognized TGA wrapper prefix')
        payload = data[:4] + data[8:]
        _, cmap, image_type = struct.unpack_from('<BBB', payload)
        width, height, depth, descriptor = struct.unpack_from('<HHBB', payload, 12)
        if cmap not in (0, 1) or image_type not in (1, 2, 3, 9, 10, 11):
            raise ValueError('Unrecognized reconstructed TGA header')
        if not width or not height or depth not in (8, 16, 24, 32) or descriptor & 0xc0:
            raise ValueError('Invalid reconstructed TGA dimensions/depth/descriptor')
        return payload, '4-byte wrapper field at offset 4 removed', 'TGA'
    raise ValueError('Unsupported extension')


def decode(path):
    raw = path.read_bytes()
    payload, layout, expected = unwrap(raw, path.suffix.lower())
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(payload)) as source:
            if source.format != expected:
                raise ValueError('Decoded format differs from expected format')
            source.load()  # Reject truncated/invalid pixels; do not enable truncated loads.
            img = source.copy()
    return img, {
        'source_bytes': len(raw), 'source_sha256': hashlib.sha256(raw).hexdigest(),
        'payload_sha256': hashlib.sha256(payload).hexdigest(),
        'layout': layout, 'format': expected, 'width': img.width,
        'height': img.height, 'mode': img.mode,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Original installation directory (read only)')
    parser.add_argument('--output', type=Path, required=True, help='New output directory outside original installation')
    parser.add_argument('--asset', action='append', default=[], help='Installation-relative asset, repeatable')
    parser.add_argument('--validate-all', action='store_true', help='Decode all supported wrappers; only export explicitly selected assets')
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    output = args.output.resolve()
    if output == root or root in output.parents:
        parser.error('Output must be outside original installation')
    if output.exists():
        parser.error('Output already exists; choose a new directory to prevent overwrites')
    selected = set()
    for rel in args.asset:
        path = (root / rel).resolve(strict=True)
        if root not in path.parents or path.suffix.lower() not in SUPPORTED:
            parser.error('Asset must be a supported file inside installation')
        selected.add(path)
    paths = sorted({p.resolve() for p in root.rglob('*') if p.is_file() and p.suffix.lower() in SUPPORTED}) if args.validate_all else sorted(selected)
    if not paths:
        parser.error('Select assets or use --validate-all')
    output.mkdir(parents=True)
    results = []
    for path in paths:
        if root not in path.parents:
            continue  # Do not follow symlink targets outside selected installation.
        record = {'path': str(path.relative_to(root))}
        try:
            img, metadata = decode(path)
            record.update(metadata, status='decoded')
            if path in selected:
                dest = output / 'images' / path.relative_to(root).with_suffix(path.suffix + '.png')
                dest.parent.mkdir(parents=True, exist_ok=True)
                img.save(dest, format='PNG')
                with Image.open(dest) as check:
                    check.load()
                    if check.size != img.size or check.tobytes() != img.tobytes():
                        raise ValueError('PNG round trip changed decoded pixels')
                record['export'] = str(dest.relative_to(output))
                record['export_sha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
            img.close()
        except Exception as exc:
            record.update(status='rejected', error=str(exc))
        results.append(record)
    failed = sum(x['status'] == 'rejected' for x in results)
    summary = {'total': len(results), 'decoded': len(results)-failed, 'rejected': failed,
               'exported': sum('export' in x for x in results)}
    (output / 'manifest.json').write_text(json.dumps({'scope': str(root), 'summary': summary, 'files': results}, indent=2)+'\n')
    print(json.dumps(summary))
    return 1 if failed else 0

if __name__ == '__main__':
    raise SystemExit(main())
