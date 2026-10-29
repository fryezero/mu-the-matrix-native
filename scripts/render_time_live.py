#!/usr/bin/env python3
"""RENDER-TIME-002: turn a read-only live capture into a RENDER-TIME-001 series.

`schedule` converts an INPUT-001 script into rtinput's event list (focus/move/ldown/lup/wheel only).
`export` reads rtsample's JSON lines, rtinput's log and mugl's statistics log, rejects torn or wide WorldTime
brackets, and writes the live series plus the private native plan: live tile and client size, the plan's script with
positions scaled to that size (the same client-area fractions rtinput replayed), the observed WorldTime epoch, and a
sample at every iteration. `pair` takes that dense native capture and keeps, for each live sample, the native row at
the live sample's recorded relative logic ordinal (never chosen by error).
Nothing here reads client memory; inputs are the local capture files. See docs/research/client-render-time.md.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import render_time as rt  # noqa: E402

BRACKET_MS = 20
# Fields the live adapter cannot observe: the clear colour is an immediate of the render scene (no memory),
# the original has one shared CRT rand() stream, and the live image has the HUD, hero equipment and other players.
UNAVAILABLE = {'sky': [0, 1, 2], 'rng': list(range(5)), 'image': list(range(48))}
VERBS = ('move', 'ldown', 'lup', 'wheel')


def parse_script(text):
    """INPUT-001 subset used by the RENDER-TIME paths: returns [(frame, verb, x, y)] in run order."""
    events = []
    for token in re.split(r'[\s;]+', re.sub(r'#[^\n]*', '', text)):
        if not token:
            continue
        frame, _, action = token.partition(':')
        verb, _, arg = action.partition(':')
        if not frame.isdigit() or not verb:
            raise ValueError(f'malformed event {token!r}')
        if verb == 'focus':
            if arg != '1' or int(frame) != 0:
                raise ValueError('only 0:focus:1 is supported live')
            continue
        if verb not in VERBS:
            raise ValueError(f'unsupported live verb {verb!r}')
        if verb == 'wheel':
            if not re.fullmatch(r'-?\d+', arg) or not -100 <= int(arg) <= 100:
                raise ValueError('bad wheel')
            events.append((int(frame), verb, int(arg), 0))
        else:
            m = re.fullmatch(r'(-?\d+),(-?\d+)', arg)
            if not m:
                raise ValueError(f'bad position {token!r}')
            events.append((int(frame), verb, int(m[1]), int(m[2])))
    events.sort(key=lambda e: e[0])   # stable: same-frame events keep file order
    if len(events) > 128:
        raise ValueError('too many events')
    return events


def scale_script(events, width, height):
    """INPUT-001 text with positions mapped to a width x height client: the fractions rtinput replays."""
    lines = ['# RENDER-TIME-002: positions scaled from 640x480 drawable pixels to the live client area', '0:focus:1']
    for frame, verb, x, y in events:
        if verb == 'wheel':
            lines.append(f'{frame}:wheel:{x}')
        else:
            lines.append(f'{frame}:{verb}:{x * width // 640},{y * height // 480}')
    return '\n'.join(lines) + '\n'


def mugl_provenance(stats_text, mask_text, mode_text):
    """Effective hotpatch mask = the last `=== hotpatch mask N` line mugl logged in this session."""
    masks = re.findall(r'^=== hotpatch mask (-?\d+):', stats_text, re.M)
    if not masks:
        raise ValueError('mugl logged no effective hotpatch mask')
    effective = int(masks[-1])
    requested = int(mask_text.split()[0]) if mask_text.split() else None
    return {'effective_mask': effective, 'requested_mask': requested, 'mask_lines': len(masks),
            'buffering_mode': mode_text.strip(), 'patches': 'off' if effective == 0 and requested == 0 else 'on'}


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def image_grid(png, title_px):
    """4x4 RGB means of the client area of a window shot (diagnostic: composition differs from native)."""
    from PIL import Image
    im = Image.open(png).convert('RGB')
    im = im.crop((0, title_px, im.width, im.height))
    cells = []
    for row in range(4):
        for col in range(4):
            box = (col * im.width // 4, row * im.height // 4, (col + 1) * im.width // 4, (row + 1) * im.height // 4)
            px = im.crop(box).resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
            cells.extend(px)
    return cells


def export(samples_path, inputs_path, plan_path, name, mugl, out_dir, provenance=None, shots=None, title_px=64):
    plan = rt.load_plan(plan_path)
    entry = next((e for e in plan['maps'] if e['name'] == name), None)
    if entry is None:
        raise ValueError(f'unknown map {name}')
    lines = read_lines(samples_path)
    pre = [l for l in lines if l['kind'] == 'preflight']
    arm = [l for l in lines if l['kind'] == 'arm']
    end = [l for l in lines if l['kind'] == 'end']
    if len(pre) != 1 or len(arm) != 1 or len(end) != 1:
        raise ValueError('capture needs one preflight, arm and end line')
    pre, arm, end = pre[0], arm[0], end[0]
    # Frame k = the first accepted post-draw read, in capture order, at least k logic steps after arm. A read is
    # rejected when a counter moved (torn) or WorldTime moved more than BRACKET_MS (the next frame had begun).
    candidates = [l for l in lines if l['kind'] == 'sample']
    if not candidates or candidates[0]['frame'] != 0 or arm['logic'] != candidates[0]['pre']['logic'] \
            or end['arm_logic'] != arm['logic']:
        raise ValueError('arm epoch does not match the frame-0 sample')
    expected = rt.schedule(plan)
    accepted, rejected, at = {}, [], 0
    for k in expected:
        while at < len(candidates):
            l = candidates[at]; at += 1
            a, b = l['pre'], l['post']
            if a['logic'] - arm['logic'] < k:
                continue
            torn = any(a[key] != b[key] for key in ('presented', 'logic', 'cframe'))
            width = b['world_time'] - a['world_time']
            if torn or not 0 <= width <= BRACKET_MS:
                rejected.append({'frame': k, 'logic': a['logic'] - arm['logic'], 'torn': torn, 'bracket_ms': width})
                continue
            accepted[k] = l
            break
    if sorted(accepted) != expected:
        raise ValueError(f'missing samples: {sorted(set(expected) - set(accepted))}')
    first = accepted[0]
    if first is not candidates[0]:
        raise ValueError('the frame-0 sample was rejected')
    worlds = {l['world'] for l in accepted.values()} | {pre['world']}
    if worlds != {entry['world']}:
        raise ValueError(f'world changed or differs from the plan: {sorted(worlds)}')
    events = [line.split() for line in Path(inputs_path).read_text().splitlines()]
    client = next((e for e in events if e[0] == 'client'), None)
    sent = [e for e in events if e[0] == 'event']
    script_events = parse_script(entry['script_path'].read_text())
    if client is None or [(int(e[1]), e[2], int(e[3]), int(e[4])) for e in sent] != script_events:
        raise ValueError('input log does not replay the plan script')
    width, height = int(client[3]), int(client[4])
    if not 320 <= width <= 4096 or not 240 <= height <= 4096:
        raise ValueError('implausible client area')
    lateness = [float(e[8]) - float(e[6]) for e in sent]
    shots = shots or {}
    rows, bracket = [], []
    for frame in expected:
        l = accepted[frame]
        grid = image_grid(shots[frame], title_px) if frame in shots else [0.0] * 48
        rows.append({'frame': frame, 'world': l['world'], 'world_time': l['pre']['world_time'],
                     'steps': l['pre']['logic'], 'camera': l['camera'], 'objects': l['objects'],
                     'particles': l['particles'], 'environment': l['environment'], 'lights': l['lights'],
                     'sky': [0.0, 0.0, 0.0, float(l['joints'])], 'rng': [0.0] * 5, 'image': grid})
        bracket.append({'frame': frame, 'world_time': [l['pre']['world_time'], l['post']['world_time']],
                        'logic': l['pre']['logic'] - arm['logic'], 'cframe': l['pre']['cframe'] - first['pre']['cframe'],
                        'presented': l['pre']['presented'] - first['pre']['presented'],
                        'read_ms': round((l['post']['host_us'] - l['pre']['host_us']) / 1000, 3),
                        'attempt': l['attempt'], 'particle_list': l['particle_list'], 'input': l.get('input')})
    tile = [int(pre['tile'][0]), int(pre['tile'][1])]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    script = out_dir / f'{name}-{width}x{height}.input'
    script.write_text(scale_script(script_events, width, height))
    frames = max(plan['frames'], bracket[-1]['logic'] + 1)
    native_plan = {'version': 1, 'width': width, 'height': height, 'frames': frames, 'sample_every': 1,
                   'save_every': -(-(frames - 1) // 2), 'start_world_time_ms': int(round(first['pre']['world_time'])),
                   'maps': [{'name': name, 'world': entry['world'], 'tile': tile, 'script': script.name,
                             # RENDER-TIME-003: the live client's UI layer (base.swf) took every recorded wheel
                             # event; native cannot hit-test base.swf, so the twin declares that state.
                             'wheel_ui_hit': True}]}
    native_plan_path = out_dir / 'native-plan.json'
    native_plan_path.write_text(json.dumps(native_plan, indent=1) + '\n')
    series = {
        'version': 1, 'source': 'live', 'draw_every_frame': False,
        'plan_sha256': rt.digest(native_plan_path), 'base_plan_sha256': rt.digest(plan_path),
        'mugl_patches': mugl['patches'], 'mugl': mugl,
        # Pool ages, animation starts, ambient phase and the shared rand() stream are not restored or observed.
        'phase': 'unaligned',
        'phase_evidence': {
            'join': {k: pre[k] for k in ('world_time', 'logic', 'cframe', 'presented')},
            'arm': {k: arm[k] for k in ('world_time', 'logic', 'cframe', 'presented')},
            'edges': end['edges'], 'torn_retries': end['torn'], 'rejected': rejected,
            'skipped_edges': [l for l in lines if l['kind'] == 'skipped_edges'],
            'samples': bracket, 'input_lateness_ms': [round(x, 2) for x in lateness],
            'client_area': [width, height], 'foreground': client[6] == '1' if len(client) > 6 else None},
        'provenance': provenance or {},
        'maps': [{'name': name, 'world': entry['world'], 'tile': tile, 'plan_tile': entry['tile'],
                  'script_sha256': rt.digest(script), 'base_script_sha256': rt.digest(entry['script_path']),
                  'expected_frames': expected,
                  'samples': rows, 'unavailable': UNAVAILABLE,
                  'image_frames': sorted(shots), 'preflight': {k: pre[k] for k in
                      ('hero', 'tile', 'hero_frame', 'hero_action', 'eye', 'angle', 'fov', 'objects')},
                  'neighbours_within_300': sum(d < 300 for d in pre['others'])}],
    }
    rt.validate_series(series)
    if any(not math.isfinite(x) for r in rows for g in rt.GROUPS for x in r[g]):
        raise ValueError('nonfinite live value')
    series['maps'][0]['coverage'] = rt.coverage(rows)
    (out_dir / 'series.json').write_text(json.dumps(series, separators=(',', ':')) + '\n')
    return series


def pair(live, native):
    """Native rows at the live samples' relative logic ordinals, relabelled with the live frame numbers."""
    rt.validate_series(live)
    rt.validate_series(native)
    if live['source'] != 'live' or native['source'] != 'native' or live['plan_sha256'] != native.get('plan_sha256'):
        raise ValueError('pair needs a live series and the native capture of its private plan')
    out = {k: v for k, v in native.items() if k != 'maps'}
    out['maps'] = []
    for e in live['maps']:
        n = next((m for m in native['maps'] if m['name'] == e['name']), None)
        if n is None:
            raise ValueError(f"native capture lacks {e['name']}")
        base = n['samples'][0]['steps']
        if n['expected_frames'] != list(range(len(n['samples']))) or \
                any(r['steps'] - base != r['frame'] for r in n['samples']):
            raise ValueError('pairing needs a native sample at every iteration, one logic step each')
        rows = []
        live0 = e['samples'][0]['steps']
        for r in e['samples']:
            step = r['steps'] - live0
            if step >= len(n['samples']):
                raise ValueError(f'native capture ends before live step {step}')
            row = dict(n['samples'][step], frame=r['frame'], native_frame=step)
            rows.append(row)
        m = {k: v for k, v in n.items() if k not in ('samples', 'coverage')}
        m.update(samples=rows, expected_frames=e['expected_frames'], coverage=rt.coverage(n['samples']))
        out['maps'].append(m)
    out['paired_by'] = 'relative logic ordinal of each live sample'
    rt.validate_series(out)
    return out


def summarize(live, paired, report, diagnostic=None):
    """Reviewed, byte-free summary of one live run: phase evidence, the per-component error vectors under
    LIVE_LIMITS (maxima over samples) and, optionally, an unscored diagnostic native capture paired the same way."""
    a, b = live['maps'][0]['samples'], paired['maps'][0]['samples']
    ev = live['phase_evidence']
    wt = [round((x['world_time'] - a[0]['world_time']) - (y['world_time'] - b[0]['world_time']), 3) for x, y in zip(a, b)]
    span_ms = a[-1]['world_time'] - a[0]['world_time']
    components = {}
    for g in rt.GROUPS:
        if g == 'rng':
            continue
        skip = set(live['maps'][0].get('unavailable', {}).get(g, ()))
        components[g] = [None if i in skip else round(max(rt.live_error(g, x[g], y[g], i) for x, y in zip(a, b)), 6)
                         for i in range(rt.GROUPS[g])]
    m = report['maps'][0]
    out = {
        'tile': live['maps'][0]['tile'], 'client_area': ev['client_area'], 'mugl': live['mugl'], 'phase': live['phase'],
        'edges': ev['edges'], 'fps': round(ev['edges'] * 1000 / span_ms, 2) if span_ms else None,
        'torn_retries': ev['torn_retries'], 'rejected_reads': len(ev['rejected']),
        'late_samples': [[s['frame'], s['logic']] for s in ev['samples'] if s['logic'] != s['frame']],
        'read_ms_max': max(s['read_ms'] for s in ev['samples']),
        'input_lateness_ms_max': max(ev['input_lateness_ms']),
        'wheel_seen': sorted({s['input']['wheel'] for s in ev['samples'] if s.get('input')}),
        'zoom_index_seen': sorted({s['input']['zoom_index'] for s in ev['samples'] if s.get('input')}),
        'world_time_rel_error_ms': [min(wt), max(wt)],
        'walk': [live['maps'][0]['coverage']['walk_distance'], paired['maps'][0]['coverage']['walk_distance']],
        'fov_span': [live['maps'][0]['coverage']['fov_span'], paired['maps'][0]['coverage']['fov_span']],
        'native_frames': [r['native_frame'] for r in b],
        'compare': {'passed': report['passed'], 'errors': report['errors'], 'failure_count': m['failure_count'],
                    'not_compared': m.get('not_compared', {})},
        'max_error': components, 'limits': {g: v for g, v in rt.LIVE_LIMITS.items() if g in components},
        'visible_objects': [[x['objects'][17] for x in a], [y['objects'][17] for y in b]],
    }
    if diagnostic is not None:
        d = diagnostic['maps'][0]['samples']
        out['diagnostic_camera_error'] = [round(max(abs(x['camera'][i] - d[x['steps'] - a[0]['steps']]['camera'][i])
                                                    for i in (0, 1, 2, 4, 5, 6, 7, 8)), 3) for x in a]
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('schedule')
    p.add_argument('script', type=Path)
    p.add_argument('out', type=Path)
    p = sub.add_parser('export')
    p.add_argument('--samples', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--plan', type=Path, default=rt.PLAN)
    p.add_argument('--map', default='00b-lorencia')
    p.add_argument('--mugl-stats', type=Path, required=True, help='mugl-stats.txt lines of this session only')
    p.add_argument('--mugl-mask', type=Path, required=True)
    p.add_argument('--mugl-mode', type=Path, required=True)
    p.add_argument('--provenance', type=Path, help='JSON with binary/DLL hashes and session notes')
    p.add_argument('--shot', action='append', default=[], help='FRAME=window.png')
    p.add_argument('--title-px', type=int, default=64)
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('summarize')
    p.add_argument('live', type=Path)
    p.add_argument('paired', type=Path)
    p.add_argument('report', type=Path)
    p.add_argument('--diagnostic', type=Path, help='unscored dense native capture of the same private plan')
    p.add_argument('--out', type=Path, required=True)
    p = sub.add_parser('pair')
    p.add_argument('live', type=Path)
    p.add_argument('native', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        if a.command == 'schedule':
            events = parse_script(a.script.read_text())
            a.out.write_text(''.join(f'{f} {v} {x} {y}\n' for f, v, x, y in events))
            print(json.dumps({'events': len(events), 'script_sha256': rt.digest(a.script)}))
            return 0
        if a.command == 'summarize':
            load = lambda path: json.loads(path.read_text())
            out = summarize(load(a.live), load(a.paired), load(a.report), load(a.diagnostic) if a.diagnostic else None)
            a.out.write_text(json.dumps(out, indent=1) + '\n')
            print(json.dumps({k: out[k] for k in ('fps', 'rejected_reads', 'world_time_rel_error_ms', 'compare')}))
            return 0
        if a.command == 'pair':
            out = pair(json.loads(a.live.read_text()), json.loads(a.native.read_text()))
            a.out.write_text(json.dumps(out, separators=(',', ':')) + '\n')
            print(json.dumps({'paired': [len(m['samples']) for m in out['maps']],
                              'native_frames': [[r['native_frame'] for r in m['samples']] for m in out['maps']]}))
            return 0
        mugl = mugl_provenance(a.mugl_stats.read_text(errors='replace'), a.mugl_mask.read_text(), a.mugl_mode.read_text())
        shots = {int(k): Path(v) for k, _, v in (s.partition('=') for s in a.shot)}
        prov = json.loads(a.provenance.read_text()) if a.provenance else None
        s = export(a.samples, a.inputs, a.plan, a.map, mugl, a.out, prov, shots, a.title_px)
        e = s['maps'][0]
        print(json.dumps({'samples': len(e['samples']), 'tile': e['tile'], 'mugl': mugl, 'coverage': e['coverage'],
                          'rejected': len(s['phase_evidence']['rejected'])}))
        return 0
    except (ValueError, KeyError, TypeError, OSError, IndexError) as error:
        print(f'render-time-live: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
