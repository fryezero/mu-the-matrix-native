#!/usr/bin/env python3
"""Read the JSON rows a native tool printed (the .stdout file run-tool.sh captured).

    summary.py FILE                  pretty-print the summary row
    summary.py FILE KEY [KEY...]     print KEY=value for summary keys; dotted paths reach nested values
    summary.py FILE --frames         one line per frame row: frame scene tag png (mu-client) or frame tile action
    summary.py FILE --logs           the log rows (mu-world, mu-walk)
    summary.py FILE --last           the last frame row, pretty-printed

Exit 1 when the file has no summary row (the tool did not finish) or a requested key is missing.
"""
import json
import pathlib
import sys


def rows(path):
    out = []
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith('{'):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def lookup(obj, dotted):
    for part in dotted.split('.'):
        if isinstance(obj, list):
            obj = obj[int(part)]
        else:
            obj = obj[part]
    return obj


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    data = rows(argv[1])
    frames = [r for r in data if ('frame' in r and not r.get('summary')) or r.get('jnl') == 'frame_in']
    if argv[2:3] == ['--frames']:
        for f in frames:
            if f.get('jnl') == 'frame_in':
                print(f"{f['scenario']} tick {f['tick']} {f['conn']} opcode {f['opcode']:#x} "
                      f"sub {f['sub']} {f['decode']} {f['apply']} {f['bytes']}")
            elif 'tag' in f:
                print(f"{f['frame']:5d} scene {f['scene']} {f['tag']:10s} {f.get('png', '')}")
            else:
                print(f"{f['frame']:5d} tile {f.get('tile')} action {f.get('action')} moving {f.get('moving')} fov {f.get('fov')}")
        return 0
    if argv[2:3] == ['--logs']:
        for r in data:
            if 'log' in r:
                print(r['log'])
        return 0
    if argv[2:3] == ['--last']:
        if not frames:
            print('no frame rows', file=sys.stderr)
            return 1
        print(json.dumps(frames[-1], indent=2))
        return 0
    summary = next((r for r in data if r.get('summary')), None)
    if summary is None:
        print('no summary row: the tool did not finish (see the .stderr and .exit files)', file=sys.stderr)
        return 1
    if len(argv) == 2:
        print(json.dumps(summary, indent=2))
        return 0
    status = 0
    for key in argv[2:]:
        try:
            print(f'{key}={json.dumps(lookup(summary, key))}')
        except (KeyError, IndexError, ValueError, TypeError):
            print(f'{key}=<missing>')
            status = 1
    return status


if __name__ == '__main__':
    sys.exit(main(sys.argv))
