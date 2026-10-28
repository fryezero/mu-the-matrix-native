#!/usr/bin/env python3
"""Run every discovered session scenario over the in-process loopback fixture.

Each migrated ops/<domain>.ops needs a <domain>-*.scn. No shared scenario list.
The skill uses the same runner with --fixture FILE and optional inbound events.
Reports and journals are local evidence; the runner never uses a sockets transport.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / 'native/fixture/scenarios'
OPS = ROOT / 'native/session/ops'
TOOL = ROOT / 'native/build/mu-session'


def discover(directory: Path, ops: Path) -> list[Path]:
    scenarios = sorted(directory.glob('*.scn'))
    if not scenarios:
        raise ValueError(f'no fixture scenarios in {directory}')
    missing = [p.stem for p in sorted(ops.glob('*.ops'))
               if not any(s.name.startswith(p.stem + '-') for s in scenarios)]
    if missing:
        raise ValueError('domains without a fixture scenario: ' + ', '.join(missing))
    return scenarios


def script_lines(script: str) -> list[str]:
    """T:inbound:HEX injects one complete plaintext frame via the fixture's send path."""
    lines = []
    for event in script.split():
        match = re.fullmatch(r'([1-9][0-9]*):inbound:([0-9a-fA-F]+)', event)
        if not match:
            raise ValueError(f'expected T:inbound:HEX, got {event!r}')
        tick, text = match.groups()
        frame = bytes.fromhex(text)
        if not frame or frame[0] not in (0xc1, 0xc2):
            raise ValueError('inbound events require plaintext C1/C2 frames')
        header = 2 if frame[0] == 0xc1 else 3
        size = int.from_bytes(frame[1:header], 'big')
        if len(frame) < header + 1 or size != len(frame):
            raise ValueError('inbound event must contain exactly one complete frame')
        command = 'send game ' + frame.hex(' ')
        # fixture.c stores the command in char text[240]. Refuse truncation.
        if len(command) >= 240 or int(tick) > 1_000_000:
            raise ValueError('inbound event exceeds fixture command/tick limit')
        lines.append(f'at {tick} {command}')
    return lines


def prepare(text: str, script: str) -> tuple[str, int]:
    """Validate the offline boundary and run through all timed commands, including server-only ones."""
    text = text.rstrip() + '\n' + '\n'.join(script_lines(script)) + '\n'
    last = 0
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if line.startswith('endpoint '):
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f'line {number}: expected endpoint ROLE HOST:PORT')
            host, port = parts[2].rsplit(':', 1)
            if not ipaddress.ip_address(host.strip('[]')).is_loopback or not 0 < int(port) < 65536:
                raise ValueError(f'line {number}: fixture endpoints must be numeric loopback addresses')
        if line.startswith('at '):
            tick = int(line.split()[1])
            if not 1 <= tick <= 1_000_000:
                raise ValueError(f'line {number}: tick outside 1..1000000')
            last = max(last, tick)
    return text, last + 20


def read_rows(stdout: str) -> list[dict]:
    return [json.loads(line) for line in stdout.splitlines() if line.startswith('{')]


def assess(rows: list[dict], returncode: int) -> dict:
    """Fail closed on missing evidence, expectation failures and any unbound inbound route."""
    errors = []
    if returncode:
        errors.append(f'mu-session exited {returncode}')
    summaries = [r['summary'] for r in rows if isinstance(r.get('summary'), dict)]
    journal = summaries[0] if len(summaries) == 1 else {}
    required = ('frames_in', 'frames_out', 'intents', 'unrecovered_intents', 'unbound_frames',
                'undecodable_frames', 'unsent_frames', 'cues', 'inputs', 'snapshots', 'ticks')
    if len(summaries) != 1 or any(type(journal.get(k)) is not int or journal[k] < 0 for k in required):
        errors.append('missing or malformed journal summary')
    frames = [r for r in rows if r.get('jnl') == 'frame_in']
    intents = [r for r in rows if r.get('jnl') == 'intent']
    unrecovered = Counter(r['kind'] for r in intents if r['status'] == 'unrecovered')
    if not frames or len(frames) != journal.get('frames_in'):
        errors.append('no inbound frames or journal frame count differs')
    if len(intents) != journal.get('intents') or sum(unrecovered.values()) != journal.get('unrecovered_intents'):
        errors.append('journal intent counts differ')
    if journal.get('unbound_frames') != 0 or any(not f.get('apply') for f in frames):
        errors.append('unbound inbound route')
    if journal.get('undecodable_frames') != 0 or any(f.get('decode') != 'ok' for f in frames):
        errors.append('undecodable inbound frame')
    if any(f.get('head') not in (0xc1, 0xc2) or f.get('encrypted') != 0 for f in frames):
        errors.append('fixture suite requires plaintext C1/C2')
    expects = [r for r in rows if 'expect' in r]
    if not expects or any(r.get('pass') is not True for r in expects):
        errors.append('missing or failed scenario expectations')
    fixture = next((r['fixture'] for r in rows if isinstance(r.get('fixture'), dict)), {})
    if (fixture.get('last_error') != '' or fixture.get('undecodable_requests') != 0
            or fixture.get('refused_connects') != 0):
        errors.append('fixture error, undecodable request or refused connection')
    transport = next((r['transport'] for r in rows if isinstance(r.get('transport'), dict)), {})
    if (transport.get('kind') != 'fixture' or transport.get('links_opened', 0) < 1
            or transport.get('links_refused') != 0):
        errors.append('expected loopback fixture transport without refused links')
    routes = Counter((f['conn'], f['opcode'], f['sub'], f['client_handler'], f['apply']) for f in frames)
    return {'pass': not errors, 'errors': errors, 'journal': journal,
            'expectations': len(expects), 'unrecovered_by_intent': dict(sorted(unrecovered.items())),
            'routes': [dict(zip(('conn', 'opcode', 'sub', 'client_handler', 'apply', 'frames'), (*key, count)))
                       for key, count in sorted(routes.items(), key=lambda item: str(item[0]))]}


def emit(row: dict) -> None:
    print(json.dumps(row, sort_keys=True), flush=True)


def run_scenario(scenario: Path, folder: Path, script: str, seed: int, timeout: float) -> dict:
    # Exclusive creation prevents a stale journal/report from being mistaken for this run.
    folder.mkdir(parents=True, exist_ok=False)
    result = {'scenario': scenario.name, 'domain': scenario.stem.split('-', 1)[0]}
    try:
        text, ticks = prepare(scenario.read_text(), script)
        local = folder / 'scenario.scn'
        local.write_text(text)
        result['source_sha256'] = hashlib.sha256(scenario.read_bytes()).hexdigest()
        result['scenario_sha256'] = hashlib.sha256(text.encode()).hexdigest()
        command = [str(TOOL), 'fixture', str(local), '--seed', str(seed), '--ticks', str(ticks),
                   '--journal', str(folder / 'session.mujnl')]
        (folder / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            (folder / 'stdout.jsonl').write_bytes(error.stdout or b'')
            (folder / 'stderr.log').write_bytes(error.stderr or b'')
            (folder / 'exit.txt').write_text('timeout\n')
            raise
        (folder / 'stdout.jsonl').write_text(process.stdout)
        (folder / 'stderr.log').write_text(process.stderr)
        (folder / 'exit.txt').write_text(str(process.returncode) + '\n')
        rows = read_rows(process.stdout)
        for row in rows:
            if 'jnl' in row or 'client' in row or 'expect' in row:
                emit({'scenario': scenario.name, **row})
        result.update(assess(rows, process.returncode))
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        result.update({'pass': False, 'errors': [str(error)], 'journal': {}, 'routes': [],
                       'expectations': 0, 'unrecovered_by_intent': {}})
    (folder / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    emit({'fixture_scenario': result})
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, help='one scenario; omitted runs every discovered scenario')
    parser.add_argument('--report', type=Path, required=True, help='new output directory')
    parser.add_argument('--script', default='', help='space-separated T:inbound:HEX events, one-based fixture ticks')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args(argv)
    try:
        if not 0 <= args.seed <= 0xffffffff or args.timeout <= 0:
            raise ValueError('seed must be uint32 and timeout must be positive')
        if args.script and not args.fixture:
            raise ValueError('--script requires --fixture FILE')
        scenarios = [args.fixture.resolve()] if args.fixture else discover(SCENARIOS, OPS)
        if not TOOL.is_file():
            raise ValueError('mu-session missing: make -C native')
        args.report = args.report.resolve()
        args.report.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as error:
        parser.exit(2, f'fixture runner: {error}\n')
    results = [run_scenario(s, args.report / s.stem, args.script, args.seed, args.timeout) for s in scenarios]
    counts = ('frames_in', 'frames_out', 'unbound_frames', 'undecodable_frames', 'unsent_frames', 'unrecovered_intents')
    totals = {k: sum(r['journal'].get(k, 0) for r in results) for k in counts}
    summary = {'summary': True, 'fixture': True, 'schema': 1,
               'commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
               'dirty': bool(subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True)),
               'binary_sha256': hashlib.sha256(TOOL.read_bytes()).hexdigest(),
               'scenarios': len(results), 'passed': sum(r['pass'] for r in results),
               'failed': sum(not r['pass'] for r in results), 'journal': totals, 'results': results}
    (args.report / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    emit(summary)
    return 1 if summary['failed'] else 0


if __name__ == '__main__':
    sys.exit(main())
