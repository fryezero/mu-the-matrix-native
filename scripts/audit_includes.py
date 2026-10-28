#!/usr/bin/env python3
"""Include audit of the session architecture (SESSION-CORE-001, docs/design/native-port/sketch/MODULES.md).

Wire and session-internal types (frames, packets, connections, links, heads, opcodes, the
CryptoModule, the route tables, domain state) must not be reachable from views. Every `#include "..."`
in native/ and reconstructed/ is resolved (relative to the including file, else by name for the
headers below, which builds reach through -I) and checked against who may include it:

  native/net/mu_link.h, mu_conn.h, mu_crypto.h     native/net, native/session, native/fixture
  native/core/mu_protocol.h                        native/core, native/net, native/session, native/fixture,
                                                   and native/tools/mu_proto.c (the protocol CLI, NATIVE-NET-001)
  native/session/session_internal.h, domains/<d>_state.h, domains/<d>.c, ops/<d>.ops,
  generated ops_all.def, bound_routes.def, routes.def, domains_all.def, session_domains_state.h
                                                   native/session only
  native/session/mu_session_tools.h                native/session, native/tools, native/tests, native/fixture
  native/session/mu_session_seed.h                 native/session, native/tools, native/tests, native/world,
                                                   native/client (seeded tool and dev builds; the header
                                                   itself refuses to compile without -DMU_SESSION_SEED)
  native/fixture/behavior.h, generated fixture_behaviors.def   native/fixture only
  native/fixture/mu_fixture.h                      native/fixture, native/tools, native/tests, native/world,
                                                   native/client (never the product mu-client: its symbol
                                                   test belongs to APP-LIVE-001)
Public headers (mu_transport.h, mu_session.h, mu_intent.h, mu_cue.h, mu_journal.h, domains/<d>.h) are
open to every module. Exit status 1 lists every violation.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ('native', 'reconstructed')
SUFFIXES = {'.c', '.h', '.cpp', '.cc', '.m', '.mm', '.inc', '.def', '.ops'}
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"')

NET_PRIVATE = ('native/net', 'native/session', 'native/fixture')
SESSION_ONLY = ('native/session',)


def rules():
    """(predicate over the resolved repo-relative path or the bare generated name, allowed dirs, label)"""
    return [
        (lambda p: p in ('native/net/mu_link.h', 'native/net/mu_conn.h', 'native/net/mu_crypto.h'),
         NET_PRIVATE, 'a net-private header'),
        (lambda p: p == 'native/core/mu_protocol.h',
         ('native/core',) + NET_PRIVATE + ('native/tools/mu_proto.c',), 'the wire protocol header'),
        (lambda p: p == 'native/session/session_internal.h' or re.fullmatch(r'native/session/domains/[^/]+_state\.h', p)
         or re.fullmatch(r'native/session/domains/[^/]+\.c', p) or re.fullmatch(r'native/session/ops/[^/]+', p)
         or p in ('gen:ops_all.def', 'gen:bound_routes.def', 'gen:routes.def', 'gen:domains_all.def',
                  'gen:session_domains_state.h'),
         SESSION_ONLY, 'a session-internal file'),
        (lambda p: p == 'native/session/mu_session_tools.h',
         ('native/session', 'native/tools', 'native/tests', 'native/fixture'), 'the session tools header'),
        (lambda p: p == 'native/session/mu_session_seed.h',
         ('native/session', 'native/tools', 'native/tests', 'native/world', 'native/client', 'native/fixture'), 'the seed header'),
        (lambda p: p in ('native/fixture/behavior.h', 'gen:fixture_behaviors.def'),
         ('native/fixture',), 'a fixture-internal file'),
        (lambda p: p == 'native/fixture/mu_fixture.h',
         ('native/fixture', 'native/tools', 'native/tests', 'native/world', 'native/client'), 'the fixture header'),
    ]


GENERATED = {'ops_all.def', 'bound_routes.def', 'routes.def', 'domains_all.def', 'session_domains_state.h',
             'fixture_behaviors.def', 'session_domains.h', 'session_intents.h'}


def guarded_by_name(root: Path) -> dict[str, str]:
    """Headers a build reaches through -I: bare name -> repo-relative path."""
    names = {}
    for rel in ('native/net/mu_link.h', 'native/net/mu_conn.h', 'native/net/mu_crypto.h', 'native/core/mu_protocol.h',
                'native/session/session_internal.h', 'native/session/mu_session_tools.h',
                'native/session/mu_session_seed.h', 'native/fixture/behavior.h', 'native/fixture/mu_fixture.h'):
        names[Path(rel).name] = rel
    for p in (root / 'native/session/domains').glob('*_state.h'):
        names[p.name] = str(p.relative_to(root))
    return names


def allowed(includer: str, dirs) -> bool:
    for d in dirs:
        if includer == d or includer.startswith(d.rstrip('/') + '/'):
            return True
    return False


def audit(root: Path) -> list[str]:
    root = root.resolve()
    by_name = guarded_by_name(root)
    checks = rules()
    problems = []
    for top in SCAN:
        base = root / top
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if path.suffix not in SUFFIXES or not path.is_file():
                continue
            rel_parts = path.relative_to(root).parts
            if 'build' in rel_parts:
                continue
            includer = str(path.relative_to(root))
            try:
                text = path.read_text(errors='replace')
            except OSError:
                continue
            for number, line in enumerate(text.splitlines(), 1):
                m = INCLUDE.match(line)
                if not m:
                    continue
                target = m.group(1)
                resolved = (path.parent / target).resolve()
                if resolved.exists():
                    try:
                        key = str(resolved.relative_to(root))
                    except ValueError:
                        continue
                elif '/' not in target and target in GENERATED:
                    key = 'gen:' + target
                elif '/' not in target and target in by_name:
                    key = by_name[target]
                else:
                    continue
                for pred, dirs, label in checks:
                    if pred(key) and not allowed(includer, dirs):
                        problems.append(f'{includer}:{number}: includes {target} ({label}; allowed from '
                                        f'{", ".join(dirs)})')
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', type=Path, default=ROOT, help='repository root to audit')
    args = ap.parse_args()
    problems = audit(args.root)
    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f'audit_includes: {len(problems)} violation(s)', file=sys.stderr)
        return 1
    print('audit_includes: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
