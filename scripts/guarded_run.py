#!/usr/bin/env python3
"""Run a program under the preview app's network guard at a lower priority (APP-POLISH-004).

macOS strips every DYLD_* variable when it executes a SIP-protected binary such as /usr/bin/nice or
/usr/bin/env. `DYLD_INSERT_LIBRARIES=libmu-nonet.dylib nice -n 10 mu-client ...` therefore starts mu-client
WITHOUT the guard. This helper keeps the guard in the child's own environment and lowers the priority in
the child itself (os.nice before exec), so no protected binary sits between it and the program:

    nice -n 10 tools/python/bin/python scripts/guarded_run.py \\
        --guard ".../Contents/Frameworks/libmu-nonet.dylib" --report nonet.json [--nice 10] -- mu-client ...

The outer `nice -n 10` only lowers this Python process; the child inherits that priority, and --nice raises
the child's niceness to at least N. The program must not itself be a SIP-protected launcher (refused).
After the run the guard's report (MU_NONET_REPORT) must exist and name "mu-nonet": it is written when the
library loads, so a missing report means the guard never loaded and the run fails (exit 3). The program's
exit status is returned otherwise; --strict also fails when the report counts a refused network call.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PROTECTED = ('/usr/bin/', '/bin/', '/sbin/', '/usr/sbin/', '/usr/libexec/', '/System/')
COUNTERS = ('inet_denied', 'other_denied', 'connects_denied', 'lookups_denied')


def resolve(program):
    found = shutil.which(program) if os.sep not in program else program
    return os.path.realpath(found) if found else program


def protected(program):
    """True for programs under the system paths whose DYLD_* environment dyld drops (SIP)."""
    return resolve(program).startswith(PROTECTED)


def child_env(guard, report, base=None):
    env = dict(os.environ if base is None else base)
    env['DYLD_INSERT_LIBRARIES'] = str(guard)
    env['MU_NONET_REPORT'] = str(report)
    return env


def lower_to(niceness):
    """preexec function: raise the niceness to at least `niceness` (never lowers it)."""
    def apply():
        current = os.getpriority(os.PRIO_PROCESS, 0)
        if niceness > current:
            os.nice(niceness - current)
    return apply


def read_report(report):
    try:
        data = json.loads(Path(report).read_text())
    except (OSError, ValueError):
        return None
    return data if data.get('guard') == 'mu-nonet' else None


def run(command, guard, report, niceness=10, strict=False, **kwargs):
    """Run `command` with the guard. Returns (exit status, report dict or None, CompletedProcess)."""
    if not command:
        raise ValueError('no program to run')
    if protected(command[0]):
        raise ValueError(f'{command[0]} is SIP-protected: dyld would drop DYLD_INSERT_LIBRARIES for it; '
                         'run the program directly (this helper sets the priority itself)')
    if not Path(guard).is_file():
        raise ValueError(f'network guard not found: {guard}')
    Path(report).unlink(missing_ok=True)
    proc = subprocess.run(command, env=child_env(guard, report, kwargs.pop('env', None)),
                          preexec_fn=lower_to(niceness), **kwargs)
    data = read_report(report)
    status = proc.returncode
    if data is None:
        status = 3
    elif strict and any(data.get(k, 0) for k in COUNTERS):
        status = 4
    return status, data, proc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--guard', required=True, help='libmu-nonet.dylib (the app bundle\'s Contents/Frameworks)')
    ap.add_argument('--report', required=True, help='the guard\'s JSON report (MU_NONET_REPORT)')
    ap.add_argument('--nice', type=int, default=10, help='minimum niceness of the program (default 10)')
    ap.add_argument('--strict', action='store_true', help='fail when the guard refused a network call')
    ap.add_argument('command', nargs=argparse.REMAINDER, help='-- program and arguments')
    args = ap.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    try:
        status, data, _ = run(command, args.guard, args.report, args.nice, args.strict)
    except ValueError as error:
        ap.exit(2, f'guarded_run: {error}\n')
    if data is None:
        print('guarded_run: the network guard did not load (no report)', file=sys.stderr)
    return status


if __name__ == '__main__':
    sys.exit(main())
