#!/usr/bin/env python3
"""Repeat static inspections into a NEW directory, retaining failures verbatim."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=pathlib.Path, help='New output directory')
parser.add_argument('--target', type=pathlib.Path, default=ROOT / 'input/main.exe')
parser.add_argument('--objdump', default='/opt/homebrew/opt/binutils/bin/objdump')
args = parser.parse_args()
target = args.target.resolve()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
rea = str(ROOT / 'tools/node_modules/.bin/rea')
env = dict(os.environ, REA_OBJDUMP_COMMAND=args.objdump)
commands = [
    ('rea-pe-resources', [rea, 'inspect-pe-resources', str(target), '--format', 'json', '--full-output']),
    *[(f'rea-{op.replace("_", "-")}', [rea, 'inspect-with-objdump', str(target), op,
                                       '--format', 'json', '--full-output'])
      for op in ['file_headers', 'section_headers', 'symbols']],
    ('pe-inventory', [sys.executable, str(ROOT / 'scripts/inspect_pe.py'), str(target)]),
    ('objdump-private-headers', [args.objdump, '-p', str(target)]),
    ('entry-disassembly', [args.objdump, '-D', '-Mintel', '--start-address=0xe646058',
                           '--stop-address=0xe646158', str(target)]),
]
digest = lambda: hashlib.sha256(target.read_bytes()).hexdigest()
manifest = {'target': str(target), 'sha256_before': digest(), 'commands': [],
            'note': 'Entry disassembly address is specific to the supplied main.exe build.'}
for name, command in commands:
    suffix = '.txt' if name in ['objdump-private-headers', 'entry-disassembly'] else '.json'
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    (output / (name + suffix)).write_bytes(result.stdout)
    (output / (name + '.stderr.txt')).write_bytes(result.stderr)
    item = dict(name=name, argv=command, process_exit_code=result.returncode)
    if name.startswith('rea-') and result.returncode == 0:
        envelope = json.loads(result.stdout)
        item['rea_ok'] = envelope.get('ok')
        record = envelope.get('data', {})
        item['evidence_id'] = record.get('evidence_id')
        raw = record.get('raw_result') or {}
        item['provider_exit_code'] = raw.get('exit_code')
    manifest['commands'].append(item)
manifest['sha256_after'] = digest()
manifest['unchanged'] = manifest['sha256_before'] == manifest['sha256_after']
(output / 'run-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
