#!/usr/bin/env python3
"""Run the `make test` unittest discoveries, one per directory in the Makefile's TEST_SUITES (GATE-PAR-001).

The suite list lives only in the top-level Makefile (`TEST_SUITES`); `make test` passes it here as arguments, and
`--list` / no arguments read the same variable, so a suite cannot be listed in one place and dropped in another
(tests/test_run_test_suites.py checks it).

  MU_GATE_JOBS=1   the sequential behaviour `make test` always had: each suite in Makefile order with its output
                   streamed, stopping at the first failing suite.
  MU_GATE_JOBS=N   a pool of N workers (default min(4, cores/2)). The longest suites start first (the durations of
                   the last run, else the built-in order below), each suite's output goes to its own log, every
                   suite runs to the end, and the summary names each suite with its counts. The exit status is
                   non-zero if any suite failed, and each failed suite's log tail is printed.

Isolation in the pool: every suite gets its own TMPDIR (tempfile.* inside it is private), and every `make` a test
starts goes through a shim that holds one lock for the duration of the build, so two suites never build into
native/build or reconstructed/* at the same time. Logs: verify-runs/test-suites-<stamp>/ (ignored).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / 'Makefile'
TIMES = ROOT / 'verify-runs' / 'test-suite-times.json'
# The longest work items as measured (GATE-PAR-001, 4 jobs at nice 10), the order of a first run with no recorded
# durations; the rest follow in Makefile order. Only an ordering hint: the suite list is TEST_SUITES.
LONGEST_FIRST = tuple(f'native/tests/test_{m}.py' for m in (
    'native_perf004', 'native_shell', 'native_app', 'native_viewer', 'native_stress', 'native_terrain',
    'native_combat', 'inventory_skin', 'native_players', 'layout', 'native_data_manifest', 'native_audio'))
# Suites run as one work item per test module in the pool (native/tests is ~all of `make test`'s time); their
# counts are summed back into one row. MU_GATE_JOBS=1 never shards.
SHARDED = ('native/tests',)
TAIL_LINES = 60

RAN = re.compile(r'^Ran (\d+) tests? in ([\d.]+)s$', re.M)
RESULT = re.compile(r'^(OK|FAILED)(?: \((.*)\))?$', re.M)


def makefile_suites(path: Path = MAKEFILE) -> list[str]:
    """TEST_SUITES from the Makefile: `TEST_SUITES = a \\` continued one directory per line."""
    text = path.read_text()
    m = re.search(r'^TEST_SUITES\s*:?=((?:[^\n]*\\\n)*[^\n]*)$', text, re.M)
    if not m:
        raise SystemExit(f'run_test_suites: no TEST_SUITES in {path}')
    return m.group(1).replace('\\\n', ' ').split()


def check_suites(suites: list[str]) -> None:
    seen = set()
    for s in suites:
        if s in seen:
            raise SystemExit(f'run_test_suites: suite {s} listed twice')
        seen.add(s)
        if not (ROOT / s).is_dir():
            raise SystemExit(f'run_test_suites: suite directory {s} does not exist')


def shown(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def default_jobs() -> int:
    return max(1, min(4, (os.cpu_count() or 2) // 2))


def jobs_from_env() -> int:
    raw = os.environ.get('MU_GATE_JOBS', '').strip()
    if not raw:
        return default_jobs()
    if not raw.isdigit() or int(raw) < 1:
        raise SystemExit(f'run_test_suites: MU_GATE_JOBS must be a positive integer, not {raw!r}')
    return int(raw)


def command(suite: str, pattern: str = 'test_*.py') -> list[str]:
    return [sys.executable, '-m', 'unittest', 'discover', '-s', suite, '-p', pattern, '-v']


def counts(log: str) -> dict:
    """The unittest summary of one discovery: ran, failures, errors, skipped (+ expected/unexpected)."""
    c = {'ran': 0, 'failures': 0, 'errors': 0, 'skipped': 0, 'expected_failures': 0, 'unexpected_successes': 0,
         'result': None}
    ran = RAN.findall(log)
    if ran:
        c['ran'] = int(ran[-1][0])
    res = RESULT.findall(log)
    if res:
        c['result'] = res[-1][0]
        for part in filter(None, (p.strip() for p in res[-1][1].split(','))):
            key, _, value = part.partition('=')
            key = key.strip().replace(' ', '_')
            if key in c and value.strip().isdigit():
                c[key] = int(value)
    return c


def passed(c: dict) -> int:
    return c['ran'] - c['failures'] - c['errors'] - c['skipped'] - c['expected_failures'] - c['unexpected_successes']


def order(work: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Longest first: by the durations the last runs recorded, a suite with no record first (it may be long);
    with no records at all, LONGEST_FIRST then the Makefile order."""
    try:
        recorded = json.loads(TIMES.read_text())
    except (OSError, ValueError):
        recorded = {}
    if recorded:
        return sorted(work, key=lambda u: (unit_id(u) in recorded, -float(recorded.get(unit_id(u), 0))))
    return sorted(work, key=lambda u: LONGEST_FIRST.index(unit_id(u)) if unit_id(u) in LONGEST_FIRST
                  else len(LONGEST_FIRST))


def record_times(durations: dict) -> None:
    try:
        old = json.loads(TIMES.read_text())
    except (OSError, ValueError):
        old = {}
    old.update({k: round(v, 1) for k, v in durations.items() if not os.path.isabs(k)})   # not ad-hoc dirs
    TIMES.parent.mkdir(parents=True, exist_ok=True)
    TIMES.write_text(json.dumps(old, indent=1, sort_keys=True) + '\n')


def summary(rows: list[tuple[str, int, float, dict]], wall: float, jobs: int) -> None:
    total = {'ran': 0, 'passed': 0, 'skipped': 0, 'failures': 0, 'errors': 0}
    print(f'\n{"suite":<32} {"status":<6} {"secs":>7} {"ran":>5} {"pass":>5} {"skip":>5} {"fail":>5} {"err":>4}')
    for suite, rc, secs, c in rows:
        status = 'ok' if rc == 0 else 'FAIL'
        print(f'{suite:<32} {status:<6} {secs:7.1f} {c["ran"]:5d} {passed(c):5d} {c["skipped"]:5d} '
              f'{c["failures"]:5d} {c["errors"]:4d}')
        for k in ('ran', 'skipped', 'failures', 'errors'):
            total[k] += c[k]
        total['passed'] += passed(c)
    failed = [r[0] for r in rows if r[1] != 0]
    print(f'run_test_suites: {len(rows)} suites, {total["ran"]} tests, {total["passed"]} passed, '
          f'{total["skipped"]} skipped, {total["failures"]} failures, {total["errors"]} errors; '
          f'{len(failed)} failed suite(s); {wall:.1f}s wall, jobs={jobs}')


def run_sequential(suites: list[str], logdir: Path) -> int:
    """MU_GATE_JOBS=1: what the Makefile's discover lines did, in order, stopping at the first failure."""
    rows, start, durations = [], time.time(), {}
    for suite in suites:
        print(' '.join(command(suite)[1:]).replace(sys.executable, '$(PYTHON)'), flush=True)
        t0 = time.time()
        log = logdir / (suite.replace('/', '_') + '.log')
        with open(log, 'w') as f:
            p = subprocess.Popen(command(suite), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, errors='replace')
            for line in p.stdout:
                sys.stdout.write(line)
                f.write(line)
            rc = p.wait()
        sys.stdout.flush()
        durations[suite] = time.time() - t0
        rows.append((suite, rc, durations[suite], counts(log.read_text(errors='replace'))))
        if rc != 0:
            break
    record_times(durations)
    summary(rows, time.time() - start, 1)
    return next((r[1] for r in rows if r[1] != 0), 0)


MAKE_SHIM = '''#!{python}
# GATE-PAR-001: serialize every `make` a test starts while the suites run in parallel.
import fcntl, os, sys
fd = os.open({lock!r}, os.O_RDWR | os.O_CREAT, 0o644)
fcntl.flock(fd, fcntl.LOCK_EX)
os.set_inheritable(fd, True)
os.execv({make!r}, [{make!r}] + sys.argv[1:])
'''


def make_shim(scratch: Path) -> Path:
    real = shutil.which('make')
    if not real:
        raise SystemExit('run_test_suites: make not found')
    bindir = scratch / 'bin'
    bindir.mkdir()
    shim = bindir / 'make'
    shim.write_text(MAKE_SHIM.format(python=sys.executable, lock=str(scratch / 'make.lock'), make=real))
    shim.chmod(0o755)
    return bindir


def units(suite: str) -> list[tuple[str, str]]:
    """(suite, pattern) work items: one per test module for a SHARDED suite, else the whole discovery. Sharding
    keeps discover's start directory (the same sys.path and import names) and loads each test_*.py on its own;
    it is refused when the directory holds a package discover would also recurse into."""
    if suite not in SHARDED:
        return [(suite, 'test_*.py')]
    d = ROOT / suite
    if any((sub / '__init__.py').exists() for sub in d.iterdir() if sub.is_dir()):
        raise SystemExit(f'run_test_suites: {suite} has a test package; it cannot be sharded per module')
    return [(suite, m.name) for m in sorted(d.glob('test_*.py'))]


def unit_id(unit: tuple[str, str]) -> str:
    return unit[0] if unit[1] == 'test_*.py' else f'{unit[0]}/{unit[1]}'


def run_parallel(suites: list[str], jobs: int, logdir: Path) -> int:
    scratch = Path(tempfile.mkdtemp(prefix='mugate-', dir='/tmp'))
    bindir = make_shim(scratch)
    work = [u for s in suites for u in units(s)]
    queue = order(work)
    print(f'run_test_suites: {len(suites)} suites ({len(work)} work items), jobs={jobs}, logs {shown(logdir)}',
          flush=True)
    lock = threading.Lock()
    results: dict[tuple[str, str], tuple[int, float, dict, Path]] = {}
    running: dict[tuple[str, str], subprocess.Popen] = {}
    stop = threading.Event()

    def worker(wid: int) -> None:
        while not stop.is_set():
            with lock:
                if not queue:
                    return
                unit = queue.pop(0)
            name = unit_id(unit).replace('/', '_')
            tmp = scratch / f'tmp-{name}'
            tmp.mkdir()
            env = dict(os.environ, TMPDIR=str(tmp) + '/', MU_GATE_WORKER=str(wid),
                       PATH=f'{bindir}{os.pathsep}{os.environ.get("PATH", "")}')
            log = logdir / f'{name}.log'
            cmd = command(*unit)
            t0 = time.time()
            with open(log, 'w') as f:
                f.write(' '.join(cmd) + '\n')
                f.flush()
                p = subprocess.Popen(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, env=env,
                                     start_new_session=True)
                with lock:
                    running[unit] = p
                rc = p.wait()
                with lock:
                    running.pop(unit, None)
            secs = time.time() - t0
            c = counts(log.read_text(errors='replace'))
            if rc == 5 and unit[1] != 'test_*.py' and c['ran'] == 0:
                rc = 0   # a helper module named test_*.py with no tests: fine inside the whole discovery
            with lock:
                results[unit] = (rc, secs, c, log)
                if rc != 0 or unit[1] == 'test_*.py':
                    print(f'  {"ok  " if rc == 0 else "FAIL"} {unit_id(unit)} ({secs:.1f}s, {c["ran"]} tests, '
                          f'{c["skipped"]} skipped)', flush=True)
            shutil.rmtree(tmp, ignore_errors=True)

    start = time.time()
    threads = [threading.Thread(target=worker, args=(i + 1,), daemon=True) for i in range(min(jobs, len(work)))]
    try:
        for t in threads:
            t.start()
        for t in threads:
            while t.is_alive():
                t.join(0.5)
    except KeyboardInterrupt:
        stop.set()
        with lock:
            for p in running.values():
                try:
                    os.killpg(p.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    shutil.rmtree(scratch, ignore_errors=True)
    record_times({unit_id(u): r[1] for u, r in results.items()})
    rows = []
    for suite in suites:
        done = [results[u] for u in units(suite) if u in results]
        if not done:
            continue
        c = {k: sum(r[2][k] for r in done) for k in done[0][2] if k != 'result'}
        rc = next((r[0] for r in done if r[0] != 0), 0)
        rows.append((suite, rc, sum(r[1] for r in done), c))
    missing = [unit_id(u) for u in work if u not in results]
    for unit in work:
        if unit in results and results[unit][0] != 0:
            rc, _, _, log = results[unit]
            tail = log.read_text(errors='replace').splitlines()[-TAIL_LINES:]
            print(f'\n===== {unit_id(unit)} failed (exit {rc}); last {len(tail)} lines of {shown(log)} =====')
            print('\n'.join(tail))
    summary(rows, time.time() - start, jobs)
    if missing:
        print(f'run_test_suites: not run: {" ".join(missing)}')
        return 1
    return 1 if any(r[1] != 0 for r in rows) else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('suites', nargs='*', help='suite directories (default: the Makefile TEST_SUITES)')
    ap.add_argument('--list', action='store_true', help='print the Makefile suite list and exit')
    ap.add_argument('--logs', type=Path, help='log directory (default verify-runs/test-suites-<stamp>)')
    a = ap.parse_args(argv)
    if a.list:
        print('\n'.join(makefile_suites()))
        return 0
    suites = a.suites or makefile_suites()
    check_suites(suites)
    jobs = jobs_from_env()
    if a.logs:
        logdir = a.logs.resolve()
        logdir.mkdir(parents=True, exist_ok=True)
    else:
        (ROOT / 'verify-runs').mkdir(exist_ok=True)
        logdir = Path(tempfile.mkdtemp(prefix=time.strftime('test-suites-%Y%m%d-%H%M%S-'), dir=ROOT / 'verify-runs'))
    return run_sequential(suites, logdir) if jobs == 1 else run_parallel(suites, jobs, logdir)


if __name__ == '__main__':
    sys.exit(main())
