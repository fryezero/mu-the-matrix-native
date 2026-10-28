#!/usr/bin/env python3
"""Compare fixed tour renders without treating missing original images as zero error.

Run fidelity_tour.py on each manifest first. This report preserves its original
masks and error metric, and separately measures the native screen-pass change.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
import fidelity_tour as tour


def compare(before, after):
    a, b = tour.load_manifest(before), tour.load_manifest(after)
    if any(a[k] != b[k] for k in ('width', 'height', 'masks')):
        raise ValueError('dimensions and masks must match')
    old = {e['name']: e for e in a['maps']}
    rows = []
    for e in b['maps']:
        name = e['name']
        p = Path(a['out_dir']) / name
        q = Path(b['out_dir']) / name
        def final(directory):
            return sorted((directory / 'frames').glob('frame-*.png'))[-1]
        left, right = final(p), final(q)
        hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (left, right)]
        live = Path(e['live_png']) if e.get('live_png') else None
        row = {'name': name, 'world': e['world'], 'before_sha256': hashes[0], 'after_sha256': hashes[1],
               'unchanged': hashes[0] == hashes[1], 'original_image_available': bool(live and live.is_file())}
        scores = [tour.compare_map(m, entry) for m, entry in ((a, old[name]), (b, e))]
        row['image_error_before'] = scores[0].get('image', {}).get('mean_abs_diff')
        row['image_error_after'] = scores[1].get('image', {}).get('mean_abs_diff')
        row['object_dump_unchanged'] = (p/'native-obj.bin').read_bytes() == (q/'native-obj.bin').read_bytes()
        row['light_dump_unchanged'] = (p/'native-light.bin').read_bytes() == (q/'native-light.bin').read_bytes()
        if hashes[0] != hashes[1]:
            x, y = [Image.open(path).convert('RGB') for path in (left, right)]
            mask = Image.new('1', x.size, 1)
            draw = ImageDraw.Draw(mask)
            for l, t, r, bottom in a['masks']:
                draw.rectangle((l, t, r-1, bottom-1), fill=0)
            count = changed = negative = absolute = 0
            sums = [0, 0, 0]
            for aa, bb, valid in zip(x.getdata(), y.getdata(), mask.getdata()):
                if not valid:
                    continue
                count += 1
                changed += aa != bb
                for k in range(3):
                    delta = bb[k] - aa[k]
                    sums[k] += delta
                    absolute += abs(delta)
                    negative += delta < 0
            row.update(scored_pixels=count, changed_pixels=changed, mean_rgb_change=[s/count for s in sums],
                       mean_abs_native_change=absolute/(3*count), negative_channels=negative)
        rows.append(row)
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before'); ap.add_argument('after'); ap.add_argument('--output', required=True)
    args = ap.parse_args()
    report = compare(args.before, args.after)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
