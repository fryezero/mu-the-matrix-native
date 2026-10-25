#!/usr/bin/env python3
"""Run the validators listed in scripts/validators.toml (VERIFY-HARNESS-001).

Every scripts/validate_*.py has one manifest row: the pins it reads (scripts/pins.py), its families, the
cases and planted mutants it is expected to report, the test that owns it, and the exact arguments that
test uses. This runner resolves the row's inputs, skips it with the missing input named when one is
absent, runs it, and checks the row's expectations against its exit status and JSON report.

  run_validators.py --list                      the rows, their pins and whether their inputs are present
  run_validators.py --only validate_hud,validate_npc --private --report DIR
  run_validators.py --private --report DIR --jobs 4
  run_validators.py --index docs/evidence-index.json --from DIR

``--private`` runs client code from the pinned captures and requires MU_RECOVERY_INTEGRATION=1, like the
private tests. Without it the runner only prints what it would run. ``--report DIR`` writes each row's
report as DIR/<name>.json, its output as DIR/<name>.log and the summary as DIR/summary.json.

Arguments may use placeholders: ``{<pin>}`` (a pins.PINS name, e.g. {text}, {data}, {flag}, {lang3}),
``{game_root}`` (MU_GAME_ROOT), ``{evidence}`` (the evidence directory), ``{math_data}`` (the math-data
capture directory), ``{report}`` (the row's report file), ``{work}`` (a fresh directory), ``{repo}``,
``{python}`` and ``{so}`` (the shared-library suffix, dylib or so).

Expectations (``expect``) map a dotted report path to a value: ``a.b`` walks dicts, an integer part indexes a
list, ``*`` fans out over a dict's values or a list's items and yields a list. A plain value must equal the
observation (every element, for a list); a table may say ``eq``, ``min``, ``max``, ``len``, ``len_min``,
``sum``, ``sum_min``, ``all_min`` (every element at least), ``truthy`` (every element true in Python's sense,
as ``all(...)`` in a test), ``contains`` (a substring) or ``same_as`` (equal to the value at another path).
``$exit`` is the exit status (0 unless the row says otherwise) and ``$stdout`` the standard output.

``prepare`` lists commands (argument lists, placeholders allowed) run in the row's work directory before
the validator; a command whose last two items are ``">"`` and a path writes its standard output there.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pins  # noqa: E402

REPO = pins.REPO
MANIFEST = REPO / 'scripts' / 'validators.toml'
PLACEHOLDER = re.compile(r'\{([a-z0-9_]+)\}')
SPECIAL = {'game_root', 'evidence', 'math_data', 'report', 'work', 'repo', 'python', 'so'}
KINDS = {'validator', 'helper'}
FIELDS = {'kind', 'parent', 'pins', 'families', 'cases', 'mutants', 'cases_at', 'mutants_at', 'test', 'args',
          'build', 'needs', 'timeout', 'expect', 'env', 'note', 'report', 'prepare'}
NEEDS = {'game_root', 'cc', 'clang'}


class ManifestError(ValueError):
    pass


def load_manifest(path=MANIFEST) -> dict[str, dict]:
    """The manifest rows by validator name, checked for shape (not for inputs)."""
    with open(path, 'rb') as handle:
        rows = tomllib.load(handle)
    for name, row in rows.items():
        unknown = set(row) - FIELDS
        if unknown:
            raise ManifestError(f'{name}: unknown fields {sorted(unknown)}')
        row.setdefault('kind', 'validator')
        if row['kind'] not in KINDS:
            raise ManifestError(f'{name}: kind must be one of {sorted(KINDS)}')
        for key in ('pins', 'families', 'args', 'build', 'needs', 'prepare'):
            row.setdefault(key, [])
            if not isinstance(row[key], list):
                raise ManifestError(f'{name}: {key} must be a list')
        row.setdefault('expect', {})
        row.setdefault('env', {})
        row.setdefault('timeout', 3600)
        row.setdefault('report', 'file' if any('{report}' in a for a in row['args']) else 'none')
        if row['kind'] == 'helper' and not row.get('parent'):
            raise ManifestError(f'{name}: a helper row names its parent')
        if row['kind'] == 'validator' and not row.get('test'):
            raise ManifestError(f'{name}: a validator row names its owning test')
        for pin in row['pins']:
            if pin not in pins.PINS:
                raise ManifestError(f'{name}: unknown pin {pin!r}')
        for need in row['needs']:
            if need not in NEEDS:
                raise ManifestError(f'{name}: unknown need {need!r}')
        for arg in row['args'] + [a for command in row['prepare'] for a in command]:
            for key in PLACEHOLDER.findall(arg):
                if key not in SPECIAL and key not in pins.PINS:
                    raise ManifestError(f'{name}: unknown placeholder {{{key}}}')
                if key in pins.PINS and key not in row['pins']:
                    raise ManifestError(f'{name}: placeholder {{{key}}} is not listed in pins')
    return rows


# ---------------------------------------------------------------------------------------------
# inputs

_digest_cache: dict[tuple[str, str, int, float], str] = {}
_digest_lock = threading.Lock()


def pin_status(pin: pins.Pin) -> tuple[str, str, Path | None]:
    """('ok'|'missing'|'mismatch', reason, path) for a pin's configured location."""
    try:
        path = pin.require()
    except pins.PinMissing as error:
        return 'missing', str(error), None
    stat = path.stat()
    key = (pin.name, str(path), stat.st_size, stat.st_mtime)
    with _digest_lock:
        cached = _digest_cache.get(key)
    if cached is None:
        try:
            pin.read()
            cached = 'ok'
        except pins.PinMismatch as error:
            cached = 'mismatch: ' + str(error)
        with _digest_lock:
            _digest_cache[key] = cached
    if cached != 'ok':
        return 'mismatch', cached[len('mismatch: '):], path
    return 'ok', '', path


def missing_needs(row) -> list[str]:
    out = []
    for need in row['needs']:
        if need == 'game_root':
            root = os.environ.get('MU_GAME_ROOT')
            if not root or not Path(root).expanduser().is_dir():
                out.append('MU_GAME_ROOT (the installed client folder) is not set or not a directory')
        elif shutil.which(need) is None:
            out.append(f'{need} is not on PATH')
    if any('{game_root}' in arg for arg in row['args']) and 'game_root' not in row['needs']:
        root = os.environ.get('MU_GAME_ROOT')
        if not root or not Path(root).expanduser().is_dir():
            out.append('MU_GAME_ROOT (the installed client folder) is not set or not a directory')
    return out


def resolve(row, report: Path, work: Path) -> tuple[list[str], dict[str, str], list[str], list[str]]:
    """(argv, input digests, missing reasons, mismatch reasons)."""
    values = {'report': str(report), 'work': str(work), 'repo': str(REPO), 'python': sys.executable,
              'game_root': str(Path(os.environ.get('MU_GAME_ROOT', '')).expanduser()),
              'evidence': str(pins.evidence_dir()), 'math_data': str(pins.math_data_dir()),
              'so': 'dylib' if sys.platform == 'darwin' else 'so'}
    missing, mismatched, used = [], [], {}
    joined = ' '.join(row['args'])
    if '{evidence}' in joined and not pins.evidence_dir().is_dir():
        missing.append(f'the evidence directory {pins.evidence_dir()} does not exist: set {pins.EVIDENCE_ENV}')
    if '{math_data}' in joined and not (pins.math_data_dir() / 'capture.json').is_file():
        missing.append(f'the math-data capture {pins.math_data_dir()} has no capture.json: set {pins.MATH_DATA_ENV}')
    for name in row['pins']:
        pin = pins.PINS[name]
        status, reason, path = pin_status(pin)
        if status == 'missing':
            missing.append(reason)
        elif status == 'mismatch':
            mismatched.append(reason)
        else:
            values[name] = str(path)
            used[name] = pin.sha256
    missing += missing_needs(row)
    fill = lambda arg: PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), arg)  # noqa: E731
    argv = [fill(arg) for arg in row['args']]
    row['_prepare'] = [[fill(arg) for arg in command] for command in row['prepare']]
    return argv, used, missing, mismatched


# ---------------------------------------------------------------------------------------------
# expectations

def lookup(report, path: str):
    """A dotted path into a JSON report; integer parts index lists; '*' sums over a dict's values or a
    list's items (each continuing with the rest of the path)."""
    parts = path.split('.')

    def walk(node, rest):
        if not rest:
            return node
        head, tail = rest[0], rest[1:]
        if head == '*':
            if not isinstance(node, (dict, list)):
                return None
            items = node.values() if isinstance(node, dict) else node
            out = []
            for item in items:
                value = walk(item, tail)
                out.extend(value if isinstance(value, list) and '*' in tail else [value])
            return out
        if isinstance(node, dict):
            return walk(node[head], tail) if head in node else None
        if isinstance(node, list) and head.lstrip('-').isdigit():
            index = int(head)
            return walk(node[index], tail) if -len(node) <= index < len(node) else None
        return None
    return walk(report, parts)


def check_expect(expected, observed) -> bool:
    try:
        if not isinstance(expected, dict):
            if isinstance(observed, list) and not isinstance(expected, list):
                return bool(observed) and all(v == expected for v in observed)
            return observed == expected
        if observed is None:
            return False
        if 'eq' in expected and observed != expected['eq']:
            return False
        if 'min' in expected and not observed >= expected['min']:
            return False
        if 'max' in expected and not observed <= expected['max']:
            return False
        if 'len' in expected and len(observed) != expected['len']:
            return False
        if 'sum' in expected and sum(observed) != expected['sum']:
            return False
        if 'all_min' in expected and not (observed and all(v >= expected['all_min'] for v in observed)):
            return False
        if 'len_min' in expected and len(observed) < expected['len_min']:
            return False
        if 'sum_min' in expected and sum(observed) < expected['sum_min']:
            return False
        if 'contains' in expected and expected['contains'] not in observed:
            return False
        if 'truthy' in expected:
            values = observed if isinstance(observed, list) else [observed]
            if bool(values) and all(bool(v) for v in values) != bool(expected['truthy']):
                return False
            if not values:
                return False
        return True
    except TypeError:
        return False


def evaluate(row, report_data, exit_code, stdout='') -> tuple[bool, dict]:
    results = {}
    ok = exit_code == 0 or '$exit' in row['expect']
    for path, expected in row['expect'].items():
        if path == '$exit':
            observed = exit_code
        elif path == '$stdout':
            observed = stdout
        else:
            observed = lookup(report_data, path) if report_data is not None else None
        if isinstance(expected, dict) and 'same_as' in expected:
            other = lookup(report_data, expected['same_as']) if report_data is not None else None
            good = observed is not None and observed == other and check_expect(
                {k: v for k, v in expected.items() if k != 'same_as'}, observed)
        else:
            good = check_expect(expected, observed)
        shown = observed if path != '$stdout' else (expected.get('contains') if good and isinstance(expected, dict)
                                                    else stdout[-200:])
        results[path] = {'expected': expected, 'observed': shown, 'ok': good}
        ok = ok and good
    return ok, results


def counts(row, report_data) -> dict:
    out = {}
    for key in ('cases', 'mutants'):
        paths = row.get(f'{key}_at')
        if not paths or report_data is None:
            continue
        paths = [paths] if isinstance(paths, str) else paths
        total = 0
        for path in paths:
            value = lookup(report_data, path)
            items = value if isinstance(value, list) and '*' in path else [value]
            for item in items:
                if isinstance(item, bool):
                    total += int(item)
                elif isinstance(item, (int, float)):
                    total += item
                elif isinstance(item, (list, dict)):
                    total += len(item)
                else:
                    total = None
                    break
            if total is None:
                break
        if total is not None:
            out[key] = total
    return out


# ---------------------------------------------------------------------------------------------
# running

_built: dict[str, tuple[int, str]] = {}
_build_lock = threading.Lock()


def build(directory: str) -> tuple[int, str]:
    with _build_lock:
        if directory not in _built:
            done = subprocess.run(['make', '-C', str(REPO / directory)], capture_output=True, text=True)
            _built[directory] = (done.returncode, done.stdout[-2000:] + done.stderr[-2000:])
        return _built[directory]


def run_row(name: str, row: dict, out_dir: Path | None = None, keep_work: bool = False) -> dict:
    """Run one manifest row; returns its summary entry (status pass/fail/skip/error)."""
    started = time.time()
    entry = {'name': name, 'test': row.get('test'), 'families': row['families'], 'pins': {}}
    if row['kind'] == 'helper':
        entry.update(status='skip', reason=f"helper module, exercised through {row['parent']}")
        return entry
    scratch = Path(tempfile.mkdtemp(prefix=f'{name}-'))
    work = scratch / 'work'
    work.mkdir()
    report = (out_dir / f'{name}.json') if out_dir else scratch / f'{name}.json'
    if report.exists():
        report.unlink()
    argv, used, missing, mismatched = resolve(row, report, work)
    entry['pins'] = used
    entry['missing_pins'] = sorted(name for name in row['pins'] if name not in used)
    if mismatched:
        entry.update(status='fail', reason='input differs from its pin: ' + '; '.join(mismatched))
        return entry
    if missing:
        entry.update(status='skip', reason='; '.join(missing))
        return entry
    for directory in row['build']:
        code, output = build(directory)
        if code:
            entry.update(status='error', reason=f'make -C {directory} failed', output=output)
            return entry
    for command in row.get('_prepare', []):
        target = None
        if len(command) > 2 and command[-2] == '>':
            command, target = command[:-2], Path(command[-1])
        done = subprocess.run(command, cwd=work, capture_output=True)
        if done.returncode:
            entry.update(status='error', reason=f'prepare step {command[0]} failed: '
                         + done.stderr.decode(errors='replace')[-300:])
            return entry
        if target is not None:
            target.write_bytes(done.stdout)
    command = [sys.executable, str(REPO / 'scripts' / f'{name}.py'), *argv]
    env = {**os.environ, **{k: str(v) for k, v in row['env'].items()}}
    entry['command'] = [str(Path(command[0]).name)] + [str(Path(c).relative_to(REPO)) if c.startswith(str(REPO))
                                                        else c for c in command[1:]]
    try:
        done = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True, timeout=row['timeout'])
        exit_code, stdout, stderr = done.returncode, done.stdout, done.stderr
    except subprocess.TimeoutExpired as error:
        exit_code = None
        stdout = error.stdout.decode(errors='replace') if isinstance(error.stdout, bytes) else (error.stdout or '')
        stderr = error.stderr.decode(errors='replace') if isinstance(error.stderr, bytes) else (error.stderr or '')
    entry['seconds'] = round(time.time() - started, 1)
    entry['exit'] = exit_code
    if out_dir:
        (out_dir / f'{name}.log').write_text(f'$ {" ".join(command)}\n--- stdout\n{stdout}\n--- stderr\n{stderr}')
    if row['report'] == 'stdout':
        data = last_json(stdout)
        if data is not None:
            report.write_text(json.dumps(data, indent=1) + '\n')
    finish(entry, row, report, exit_code, stdout, stderr, bool(out_dir))
    if not keep_work:
        shutil.rmtree(scratch, ignore_errors=True)
    return entry


def finish(entry, row, report: Path, exit_code, stdout, stderr, keep_name=True) -> dict:
    """Judge a finished run from its exit status, report file and output (also used by --recheck)."""
    for key in ('report', 'report_sha256', 'report_error', 'reason', 'expect', 'cases', 'mutants'):
        entry.pop(key, None)
    report_data = None
    if row['report'] in ('file', 'stdout') and report.exists():
        try:
            report_data = json.loads(report.read_text())
            entry['report'] = report.name if keep_name else None
            entry['report_sha256'] = pins.sha256_file(report)
        except json.JSONDecodeError as error:
            entry['report_error'] = str(error)
    if exit_code is None:
        entry.update(status='error', reason=f"timed out after {row['timeout']} s")
        return entry
    ok, expectations = evaluate(row, report_data, exit_code, stdout)
    observed = counts(row, report_data)
    for key, value in observed.items():   # the expected case and mutant counts are expectations too
        if row.get(key) is not None:
            good = value == row[key]
            expectations[f'#{key}'] = {'expected': row[key], 'observed': value, 'ok': good}
            ok = ok and good
    entry['expect'] = expectations
    entry.update(observed)
    if row['report'] == 'file' and report_data is None and exit_code == 0:
        ok = False
        entry['reason'] = 'no JSON report was written'
    entry['status'] = 'pass' if ok else 'fail'
    if not ok and 'reason' not in entry:
        tail = (stderr.strip() or stdout.strip()).splitlines()[-3:]
        bad = [k for k, v in expectations.items() if not v['ok']]
        entry['reason'] = (f'exit {exit_code}' if exit_code else 'expectations ' + ', '.join(bad)) + \
            (': ' + ' | '.join(tail) if tail else '')
    return entry


def recheck(rows: dict, directory: Path) -> dict:
    """Re-judge a --report directory against the current manifest without running anything."""
    summary = json.loads((directory / 'summary.json').read_text())
    for name, entry in summary['rows'].items():
        if name not in rows or entry.get('status') == 'skip' or 'exit' not in entry:
            continue
        log = directory / f'{name}.log'
        stdout = stderr = ''
        if log.exists():
            text = log.read_text()
            head, _, rest = text.partition('\n--- stdout\n')
            stdout, _, stderr = rest.partition('\n--- stderr\n')
        finish(entry, rows[name], directory / f'{name}.json', entry['exit'], stdout, stderr)
    write_summary(directory, summary)
    return summary


def last_json(text: str):
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def environment() -> dict:
    try:
        commit = subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = None
    try:
        import unicorn
        unicorn_version = unicorn.__version__
    except ImportError:
        unicorn_version = None
    return {'commit': commit, 'python': sys.version.split()[0], 'unicorn': unicorn_version,
            'platform': sys.platform, 'evidence_dir': 'MU_EVIDENCE_DIR' if os.environ.get('MU_EVIDENCE_DIR')
            else 'repository evidence/', 'game_root_set': bool(os.environ.get('MU_GAME_ROOT')),
            'snapshot_dir_set': bool(os.environ.get('MU_SNAPSHOT_DIR'))}


def select(rows: dict, only: str | None) -> list[str]:
    if not only:
        return list(rows)
    wanted = [w.strip() for w in only.split(',') if w.strip()]
    names = [n for n in rows if any(fnmatch.fnmatch(n, w) or n == f'validate_{w}' for w in wanted)]
    unknown = [w for w in wanted if not any(fnmatch.fnmatch(n, w) or n == f'validate_{w}' for n in rows)]
    if unknown:
        raise SystemExit(f'no manifest row matches {unknown}')
    return names


def list_rows(rows: dict, names: list[str]) -> None:
    for name in names:
        row = rows[name]
        if row['kind'] == 'helper':
            print(f'{name:40} helper of {row["parent"]}')
            continue
        states = []
        for pin in row['pins']:
            status, _, _ = pin_status(pins.PINS[pin])
            states.append(pin if status == 'ok' else f'{pin}:{status}')
        if missing_needs(row):
            states.append('needs:missing')
        print(f'{name:40} {" ".join(states):50} {row.get("test", "")}')


def public(text: str) -> str:
    """A reason without local paths: the evidence, snapshot and repository directories and the home folder
    become their variables."""
    replacements = [(str(pins.evidence_dir()), '$MU_EVIDENCE_DIR'), (str(REPO), '<repo>')]
    if pins.snapshot_dir():
        replacements.insert(0, (str(pins.snapshot_dir()), '$MU_SNAPSHOT_DIR'))
    if os.environ.get('MU_GAME_ROOT'):
        replacements.insert(0, (str(Path(os.environ['MU_GAME_ROOT']).expanduser()), '$MU_GAME_ROOT'))
    replacements.append((str(Path.home()), '~'))
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def write_index(index_path: Path, summary: dict, note: str | None = None) -> None:
    """Regenerate the validators part of docs/evidence-index.json from a summary; everything else (the
    human-written findings and the other validation fields) is kept as it is."""
    index = json.loads(index_path.read_text())
    validation = index.setdefault('validation', {})
    rows, helpers = {}, []
    for name, entry in sorted(summary['rows'].items()):
        if entry.get('status') == 'skip' and str(entry.get('reason', '')).startswith('helper module'):
            helpers.append(name)
            continue
        row = {'status': entry['status'], 'test': entry.get('test')}
        for key in ('cases', 'mutants'):
            if entry.get(key) is not None:
                row[key] = entry[key]
        if entry.get('reason'):
            row['reason'] = public(entry['reason'])
        if entry.get('expect'):
            good = sum(1 for check in entry['expect'].values() if check['ok'])
            row['checks'] = f"{good}/{len(entry['expect'])} report expectations"
        if entry.get('pins'):
            row['pins'] = sorted(entry['pins'])
        rows[name] = row
    states = [row['status'] for row in rows.values()]
    validation['validators'] = {
        'generated_by': 'scripts/run_validators.py --private (VERIFY-HARNESS-001)',
        'date': summary['date'], 'commit': summary['environment'].get('commit'),
        **({'note': note} if note else {}),
        'environment': summary['environment'],
        'totals': {state: states.count(state) for state in ('pass', 'fail', 'error', 'skip')},
        'pins': {name: pin.sha256 for name, pin in pins.PINS.items()}, 'rows': rows,
        'helpers': {'parent_runs_them': helpers}}
    index['updated'] = summary['date']
    index_path.write_text(splice(index_path.read_text(), index))


def _value_end(text: str, start: int) -> int:
    """Index just past the JSON object or array that opens at text[start]."""
    depth, i, quoted = 0, start, False
    while i < len(text):
        c = text[i]
        if quoted:
            if c == '\\':
                i += 1
            elif c == '"':
                quoted = False
        elif c == '"':
            quoted = True
        elif c in '{[':
            depth += 1
        elif c in '}]':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError('unbalanced JSON')


def splice(text: str, index: dict) -> str:
    """The index text with only its top-level "updated" and "validation" values replaced, so the
    hand-formatted findings keep their layout."""
    out = re.sub(r'^(\s*"updated":\s*)"[^"]*"', lambda m: m.group(1) + json.dumps(index['updated']), text,
                 count=1, flags=re.M)
    match = re.search(r'^  "validation":\s*', out, re.M)
    if not match:
        return json.dumps(index, indent=2) + '\n'
    start = match.end()
    end = _value_end(out, start)
    body = json.dumps(index['validation'], indent=2).replace('\n', '\n  ')
    result = out[:start] + body + out[end:]
    if json.loads(result) != index:
        raise ValueError('index splice changed more than the validation section')
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--list', action='store_true', help='list the rows and the state of their inputs')
    parser.add_argument('--only', help='comma-separated row names or globs (validate_hud, validate_social2*)')
    parser.add_argument('--private', action='store_true', help='run them (needs MU_RECOVERY_INTEGRATION=1)')
    parser.add_argument('--report', type=Path, help='write <name>.json, <name>.log and summary.json here')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--index', type=Path, help='regenerate this evidence index from --from DIR/summary.json')
    parser.add_argument('--from', dest='source', type=Path, help='a --report directory to build --index from')
    parser.add_argument('--note', help='with --index: a sentence recorded with the regenerated rows')
    parser.add_argument('--recheck', type=Path, help='re-judge a --report directory against the manifest')
    parser.add_argument('--resume', action='store_true',
                        help='with --report: keep its finished rows, run the missing and killed ones')
    args = parser.parse_args(argv)
    rows = load_manifest(args.manifest)
    if args.recheck:
        summary = recheck(rows, args.recheck)
        print_totals(summary)
        return 0
    if args.index:
        if not args.source:
            raise SystemExit('--index needs --from DIR (a previous --report directory)')
        write_index(args.index, json.loads((args.source / 'summary.json').read_text()), args.note)
        print(f'{args.index}: validators regenerated from {args.source / "summary.json"}')
        return 0
    names = select(rows, args.only)
    if args.list:
        list_rows(rows, names)
        return 0
    if not args.private:
        for name in names:
            row = rows[name]
            if row['kind'] == 'validator':
                print(name, ' '.join(row['args']))
        print('(dry run: add --private with MU_RECOVERY_INTEGRATION=1 to run them)')
        return 0
    if os.environ.get('MU_RECOVERY_INTEGRATION') != '1':
        raise SystemExit('--private runs client code from the pinned captures: set MU_RECOVERY_INTEGRATION=1')
    if args.report:
        args.report.mkdir(parents=True, exist_ok=True)
    summary = {'date': datetime.date.today().isoformat(), 'environment': environment(), 'rows': {}}
    if args.resume:
        if not args.report or not (args.report / 'summary.json').exists():
            raise SystemExit('--resume needs --report DIR with a summary.json from an earlier run')
        summary['rows'] = json.loads((args.report / 'summary.json').read_text())['rows']
        # keep finished rows; rerun the missing ones and those the system killed (negative exit) or timed out
        done = {n for n, e in summary['rows'].items()
                if e.get('status') in ('pass', 'fail', 'skip') and (e.get('exit') is None or e['exit'] >= 0)}
        names = [n for n in names if n not in done]
        for name in names:
            summary['rows'].pop(name, None)
    lock = threading.Lock()

    def one(name):
        entry = run_row(name, rows[name], args.report)
        with lock:
            summary['rows'][name] = entry
            print(f"{entry['status']:5} {name:40} {entry.get('seconds', 0):8.1f}s  {entry.get('reason', '')[:160]}",
                  flush=True)
            if args.report:
                write_summary(args.report, summary)
        return entry

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        list(pool.map(one, names))
    totals = summarize(summary)
    if args.report:
        write_summary(args.report, summary)
    print_totals(summary)
    return 0 if totals['fail'] == 0 and totals['error'] == 0 else 1


def summarize(summary: dict) -> dict:
    states = [entry['status'] for entry in summary['rows'].values()]
    summary['totals'] = {state: states.count(state) for state in ('pass', 'fail', 'error', 'skip')}
    summary['rows'] = dict(sorted(summary['rows'].items()))
    return summary['totals']


def print_totals(summary: dict) -> None:
    totals = summarize(summary)
    print(f"{totals['pass']} pass, {totals['fail']} fail, {totals['error']} error, {totals['skip']} skip")


def write_summary(directory: Path, summary: dict) -> None:
    summarize(summary)
    (directory / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
