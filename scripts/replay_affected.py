#!/usr/bin/env python3
"""Replay the affected selection of merged PRs with a previous selector and the current one (TEST-SPEED-004).

  replay_affected.py SPEC.json --out RESULT.json [--work DIR] [--only PR,PR]

SPEC (docs/testing/test-speed-004-selection.json has the one used for TEST-SPEED-004):

  {"old": "<commit whose scripts/affected.py, run_validators.py, run_test_suites.py are the previous selector>",
   "cases": [
     {"pr": 306, "mode": "lane", "tree": "<lane head>", "base": "<main the lane diffed against>", "suites": true},
     {"pr": 306, "mode": "since", "tree": "<merged commit>",
      "tested": [["7b7c260e", "*"], ["354e03c8", ["validate_combat", "validate_particles"]]],
      "lane_rows": ["validate_fidelity", "..."], "steward_ran": ["validate_fidelity", "..."]},
     {"pr": 287, "mode": "lane", "tree": "724ad10a", "base": "...", "suites": true,
      "must_suites": ["native/tests/test_native_worlds_l.py"], "must_rows": []}]}

lane:  what `--affected <base>` selects at the lane head (diff merge-base(base, tree)..tree).
since: the steward's question at the merged tree: which of the PR's tested rows (lane_rows; all rows if absent)
       have inputs that differ between their tested commit ("*": the rows no other group names) and the tree. The previous selector
       is asked the same question (`--list-affected <tested>` with the tested commit an ancestor of the tree).

Each tree is a temporary detached worktree; both selectors run in fresh processes with it as their repository
(their files, original_cache.py included, are copied into <tree>/.replay-old and .replay-new next to the
tree's own pins.py). Nothing is built; the worktrees are removed afterwards.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = ('affected.py', 'run_validators.py', 'run_test_suites.py', 'original_cache.py')
CHILD = r'''
import json, sys
from pathlib import Path
here = Path(sys.argv[1]); root = here.parent
sys.path.insert(0, str(here))
import affected, run_validators as rv, run_test_suites as rts
job = json.loads(sys.stdin.read())
new = hasattr(affected, 'TOOLING')
rows = rv.load_manifest(root / 'scripts' / 'validators.toml')
units = rv.row_units(rows, root) if new else None
out = {'rows': {}, 'suites': {}, 'fallback': {}, 'total_rows': len(rows)}
if new:
    out['fallback'] = affected.fallback_units(units)
for ref, changed in job['groups']:
    if new:
        why = rv.affected_rows(rows, ref, root=root, changed=changed, since=job['since'], units=units)
    else:
        why = rv.affected_rows(rows, ref, root=root, changed=changed)
    out['rows'][ref] = why
    if job['suites']:
        suites = rts.makefile_suites()
        out['total_suites'] = sum(len(rts.units(s)) for s in suites)
        if new:
            out['suites'][ref] = rts.affected_units(suites, ref, changed=changed, root=root, since=job['since'])
        else:
            out['suites'][ref] = rts.affected_units(suites, ref, changed=changed, root=root)
print(json.dumps(out))
'''


def git(*args, cwd=ROOT) -> str:
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def changed(base: str, tree: str) -> list[str]:
    return sorted(p for p in git('diff', '--no-renames', '--name-only', base, tree).splitlines() if p)


def selector_dir(tree_dir: Path, name: str, source: dict[str, str]) -> Path:
    folder = tree_dir / f'.replay-{name}'
    folder.mkdir()
    (folder / '.gitignore').write_text('*\n')
    for file in ('pins.py',):
        if (tree_dir / 'scripts' / file).is_file():
            shutil.copy(tree_dir / 'scripts' / file, folder / file)
    for file, text in source.items():
        (folder / file).write_text(text)
    return folder


def run(folder: Path, job: dict) -> tuple[dict, float]:
    started = time.time()
    done = subprocess.run([sys.executable, '-c', CHILD, str(folder)], input=json.dumps(job), capture_output=True,
                          text=True, cwd=folder.parent)
    if done.returncode:
        raise SystemExit(f'replay: selector in {folder} failed:\n{done.stderr[-3000:]}')
    return json.loads(done.stdout.strip().splitlines()[-1]), time.time() - started


def combine(case: dict, result: dict, key: str) -> dict[str, list[str]]:
    """Per tested group: the rest of the rows (of lane_rows, if given) for '*', else only the named ones."""
    named = {row for _, members in case['_groups'] for row in (members if members != '*' else [])}
    scope = set(case['lane_rows']) if key == 'rows' and 'lane_rows' in case else None
    out: dict[str, list[str]] = {}
    for ref, members in case['_groups']:
        for name, reasons in result[key].get(ref, {}).items():
            if scope is not None and name not in scope:
                continue
            if (members == '*' and name not in named) or (members != '*' and name in members):
                out.setdefault(name, reasons)
    return out


def replay(spec: dict, work: Path, only: set[int] | None) -> list[dict]:
    old = {f: git('show', f"{spec['old']}:scripts/{f}") for f in SELECTOR}
    new = {f: (ROOT / 'scripts' / f).read_text() for f in SELECTOR}
    results = []
    for case in spec['cases']:
        if only and case['pr'] not in only:
            continue
        tree = git('rev-parse', case['tree']).strip()
        if case['mode'] == 'lane':
            base = git('merge-base', case['base'], tree).strip()
            case['_groups'] = [(base, '*')]
        else:
            case['_groups'] = [(git('rev-parse', ref).strip(), members) for ref, members in case['tested']]
        groups = [(ref, changed(ref, tree)) for ref, _ in case['_groups']]
        job = {'groups': groups, 'since': case['mode'] == 'since', 'suites': bool(case.get('suites'))}
        tree_dir = work / f"{case['pr']}-{case['mode']}-{tree[:8]}"
        git('worktree', 'add', '--detach', '-f', str(tree_dir), tree)
        try:
            before, before_s = run(selector_dir(tree_dir, 'old', old), job)
            after, after_s = run(selector_dir(tree_dir, 'new', new), job)
        finally:
            git('worktree', 'remove', '--force', str(tree_dir))
        rows_before, rows_after = combine(case, before, 'rows'), combine(case, after, 'rows')
        entry = {k: v for k, v in case.items() if not k.startswith('_')}
        entry.update(
            tree=tree, groups=[[ref, members] for ref, members in case['_groups']],
            changed={ref: paths for ref, paths in groups},
            rows_total=after['total_rows'], rows_before=sorted(rows_before), rows_after=sorted(rows_after),
            reasons_after={n: r[:3] for n, r in sorted(rows_after.items())},
            removed_reasons_before={n: rows_before[n][:3] for n in sorted(set(rows_before) - set(rows_after))},
            fallback_after=after['fallback'], seconds_before=round(before_s, 2), seconds_after=round(after_s, 2))
        if job['suites']:
            suites_before, suites_after = combine(case, before, 'suites'), combine(case, after, 'suites')
            entry.update(suites_total=after.get('total_suites'), suites_before=sorted(suites_before),
                         suites_after=sorted(suites_after))
        misses = {}
        for key, have in (('must_rows', rows_after), ('must_suites', entry.get('suites_after', []))):
            missing = sorted(set(case.get(key, [])) - set(have))
            if missing:
                misses[key] = missing
        entry['misses'] = misses
        entry['steward_ran_not_selected'] = sorted(set(case.get('steward_ran', [])) - set(rows_after))
        results.append(entry)
        print(f"#{case['pr']} {case['mode']:5} rows {len(rows_before):3} -> {len(rows_after):3}"
              + (f"  suites {len(entry['suites_before']):3} -> {len(entry['suites_after']):3}" if job['suites'] else '')
              + f"  ({before_s:.1f} s / {after_s:.1f} s)  misses {misses or 0}"
              + (f"  steward-ran-not-selected {entry['steward_ran_not_selected']}" if entry['steward_ran_not_selected'] else ''),
              flush=True)
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('spec', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--work', type=Path, default=Path(os.environ.get('TMPDIR', '/tmp')) / 'replay-affected')
    ap.add_argument('--only', help='comma-separated PR numbers')
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text())
    a.work.mkdir(parents=True, exist_ok=True)
    only = {int(n) for n in a.only.split(',')} if a.only else None
    results = replay(spec, a.work.resolve(), only)
    a.out.write_text(json.dumps({'old': spec['old'], 'cases': results}, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
