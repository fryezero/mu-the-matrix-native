#!/usr/bin/env python3
"""Measure Icarus frame sequences and draw-only ablations with the tour's unchanged HUD masks.
Inputs and reports stay local. --renders holds after25/, after400/, series/, no-cover/, no-emitter/,
no-dragons/, no-puffs/, no-swirls/. The ablations suppress drawing only, preserving RNG and movement.
--previous holds RENDER-WORLDS-C's before/, before400/, after/, after400/.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops
import fidelity_tour as tour


def footprint(a, b):
    d = ImageChops.difference(a, b)
    r, g, blue = d.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), blue).point(lambda v: 255 if v > 1 else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--renders', type=Path, required=True)
    ap.add_argument('--previous', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    m = tour.load_manifest(a.manifest)
    e = next(e for e in m['maps'] if e['world'] == 10)
    live = tour.client_area(e['live_png'], m['width'], m['height'], m['title_bar'])
    out = {'live_sha256': hashlib.sha256(Path(e['live_png']).read_bytes()).hexdigest(),
           'method': 'whole-scene score unchanged; element masks are draw-only difference footprints > 1 RGB unit',
           'samples': {}, 'series': []}
    for frame, suffix in [(24, ''), (399, '400')]:
        def read(root, lane):
            return Image.open(root/lane/'10-icarus/frames'/f'frame-{frame:04d}.png').convert('RGB')
        final = read(a.renders, 'after25' if frame == 24 else 'after400')
        pre = read(a.previous, 'before'+suffix)
        post = read(a.previous, 'after'+suffix)
        images = {'pre_C':pre, 'post_C':post, 'C2':final}
        scores = {k:tour.compare_images(live, im, m['masks'])[0] for k, im in images.items()}
        masks = {'C_phase_change':footprint(pre, post)}
        for name in ['cover', 'emitter', 'dragons', 'puffs', 'swirls']:
            ablated = read(a.renders, 'no-'+name)
            scores['no_'+name] = tour.compare_images(live, ablated, m['masks'])[0]
            masks[name] = footprint(final, ablated)
        # Keep one fixed phase-change mask for before/after, with its complement also scored.
        masks['C_phase_unchanged'] = ImageChops.invert(masks['C_phase_change'])
        elements = {}
        md = a.renders/'masks'/str(frame); md.mkdir(parents=True, exist_ok=True)
        for name, mask in masks.items():
            mask.save(md/(name+'.png'))
            if not ImageChops.multiply(mask, tour.mask_image(live.size, m['masks'])).getbbox():
                elements[name] = {'pixels':0}; continue
            elements[name] = {k:tour.compare_images(live, im, m['masks'], include_mask=mask)[0]
                              for k, im in images.items()}
        out['samples'][str(frame)] = {'whole':scores, 'elements':elements}
    for p in sorted((a.renders/'series/10-icarus/frames').glob('frame-*.png')):
        im = Image.open(p).convert('RGB')
        score = tour.compare_images(live, im, m['masks'])[0]
        out['series'].append({'frame':int(p.stem.split('-')[-1]), **score})
    if out['series']:
        values = [r['mean_abs_diff'] for r in out['series']]
        out['series_summary'] = {'frames':len(values), 'min':min(values), 'max':max(values),
                                 'mean':sum(values)/len(values), 'first':out['series'][0]['frame'],
                                 'last':out['series'][-1]['frame']}
    out['other_capture_hashes'] = {}
    for p in sorted((a.renders/'after25').glob('*/frames/frame-0024.png')):
        name = p.parent.parent.name
        if name == '10-icarus': continue
        before = a.previous/'after'/name/'frames'/p.name
        out['other_capture_hashes'][name] = hashlib.sha256(p.read_bytes()).hexdigest() == hashlib.sha256(before.read_bytes()).hexdigest()
    a.output.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps({'scores': {f:{k:v['mean_abs_diff'] for k,v in r['whole'].items()} for f,r in out['samples'].items()},
                      'series':out.get('series_summary'), 'other_hashes_unchanged':sum(out['other_capture_hashes'].values())}, indent=2))

if __name__ == '__main__': main()
