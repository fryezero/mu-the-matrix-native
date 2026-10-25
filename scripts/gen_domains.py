#!/usr/bin/env python3
"""Generate the session's lists from the files that exist (SESSION-CORE-001).

Inputs (nothing here is hand-synced: adding a domain, a route binding, an intent kind or a fixture
behaviour never edits a shared list):

  native/session/domains/<d>_state.h   a domain's private state  -> MU_DOMAIN(<d>)
  native/session/domains/<d>.h         its public getters         -> included by session_domains.h
  native/session/domains/<d>.intents   MU_INTENT_KIND(NAME, field, payload type) rows
  native/session/ops/<d>.ops           MU_OP(opcode, sub, apply_fn) and MU_SUBMIT(MU_INTENT_X, submit_fn)
  native/net/dispatch.def              THE route table (wire-research lane, generated from the client)
    or native/net/dispatch.seed.def    the seed (MU_STATIC rows) while dispatch.def does not exist
  native/net/ignore.def                MU_IGNORE(opcode, sub, "reason") rows (optional)
  native/fixture/behaviors/<b>.c       one `const mu_fixture_behavior mu_fx_<b>` each

Outputs (build/gen): session_domains.h, domains_all.def, session_domains_state.h, ops_all.def,
routes.def, bound_routes.def, session_intents.h, fixture_behaviors.def, gen_domains.json.

The build fails (exit 1, every violation listed) when
  - a domain has state but no ops file or public header, or the reverse;
  - an MU_OP names a route the table lacks;
  - two MU_OP rows bind one route (also a duplicate `case` in dispatch.c);
  - an MU_OP and an MU_IGNORE share a route;
  - the route table repeats a family or a route;
  - two .intents files define one kind or field, an MU_SUBMIT names an unknown kind, two MU_SUBMIT
    rows route one kind (also an initializer override in dispatch.c), or a kind has no MU_SUBMIT;
  - two fixture behaviours share a name, or a behaviour file does not define mu_fx_<name>.

--no-checks writes the outputs even when rules are broken. It exists only for the negative build
test, which shows that the compiler refuses the duplicates the generator would have reported.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INT = r'(?:0[xX][0-9a-fA-F]+|[0-9]+)'
SUB = r'(?:' + INT + r'|MU_SUB_NONE)'
ADDR = r'(?:' + INT + r'u?|MU_ADDR_UNVERIFIED)'
AT = r'(?:' + INT + r'|MU_AT_UNKNOWN)'

RE_FAMILY = re.compile(r'^MU_FAMILY\(\s*(' + INT + r')\s*,\s*(' + AT + r')\s*,\s*(' + AT + r')\s*,\s*(' + ADDR +
                       r')\s*\)$')
RE_ROUTE = re.compile(r'^MU_ROUTE\(\s*(' + INT + r')\s*,\s*(' + SUB + r')\s*,\s*(' + ADDR + r')\s*,\s*(MU_[A-Z]+)\s*\)$')
RE_OP = re.compile(r'^MU_OP\(\s*(' + INT + r')\s*,\s*(' + SUB + r')\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$')
RE_SUBMIT = re.compile(r'^MU_SUBMIT\(\s*(MU_INTENT_[A-Z0-9_]+)\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$')
RE_IGNORE = re.compile(r'^MU_IGNORE\(\s*(' + INT + r')\s*,\s*(' + SUB + r')\s*,\s*("(?:[^"\\]|\\.)*")\s*\)$')
RE_KIND = re.compile(r'^MU_INTENT_KIND\(\s*([A-Z][A-Z0-9_]*)\s*,\s*([a-z_][a-z0-9_]*)\s*,\s*(.+)\)$')


def strip_comments(text: str) -> list[tuple[int, str]]:
    """Lines without /* */ and // comments, keeping line numbers (comments may span lines)."""
    out = []
    in_block = False
    for number, raw in enumerate(text.splitlines(), 1):
        line, i = [], 0
        while i < len(raw):
            if in_block:
                end = raw.find('*/', i)
                if end < 0:
                    i = len(raw)
                else:
                    in_block, i = False, end + 2
            elif raw.startswith('/*', i):
                in_block, i = True, i + 2
            elif raw.startswith('//', i):
                break
            elif raw[i] == '"':
                end = i + 1
                while end < len(raw) and raw[end] != '"':
                    end += 2 if raw[end] == '\\' else 1
                line.append(raw[i:end + 1])
                i = end + 1
            else:
                line.append(raw[i])
                i += 1
        s = ''.join(line).strip()
        if s:
            out.append((number, s))
    return out


def num(token: str) -> int:
    return int(token.rstrip('u'), 0)


def sub_key(token: str):
    return 'MU_SUB_NONE' if token == 'MU_SUB_NONE' else num(token)


def fmt_sub(sub) -> str:
    return sub if isinstance(sub, str) else '0x%02x' % sub


def fmt_addr(token: str) -> str:
    return token if token == 'MU_ADDR_UNVERIFIED' else '0x%08xu' % num(token)


class Gen:
    def __init__(self, session: Path, net: Path, fixture: Path, routes: Path | None):
        self.session, self.net, self.fixture = session, net, fixture
        self.errors: list[str] = []
        if routes is None:
            real = net / 'dispatch.def'
            routes = real if real.exists() else net / 'dispatch.seed.def'
        self.routes_file = routes

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(ROOT))
        except ValueError:
            return str(p)

    # ---- inputs ---------------------------------------------------------------------------------

    def read_domains(self) -> list[str]:
        d = self.session / 'domains'
        state = {p.name[:-len('_state.h')] for p in d.glob('*_state.h')}
        ops = {p.stem for p in (self.session / 'ops').glob('*.ops')}
        public = {p.stem for p in d.glob('*.h') if not p.name.endswith('_state.h')}
        for name in sorted(state - ops):
            self.fail(f'domain {name}: domains/{name}_state.h has no ops/{name}.ops')
        for name in sorted(ops - state):
            self.fail(f'domain {name}: ops/{name}.ops has no domains/{name}_state.h')
        for name in sorted(state - public):
            self.fail(f'domain {name}: domains/{name}_state.h has no public header domains/{name}.h')
        return sorted(state & ops)

    def read_table(self):
        families, routes = {}, []
        if not self.routes_file.exists():
            self.fail(f'no route table: {self.rel(self.routes_file)}')
            return families, routes
        seen = {}
        for line, text in strip_comments(self.routes_file.read_text()):
            where = f'{self.routes_file.name}:{line}'
            m = RE_FAMILY.match(text)
            if m:
                op = num(m.group(1))
                if op in families:
                    self.fail(f'{where}: MU_FAMILY(0x{op:02x}) repeats {families[op]["where"]}')
                families[op] = {'c1': m.group(2), 'c2': m.group(3), 'addr': m.group(4), 'where': where}
                continue
            m = RE_ROUTE.match(text)
            if m:
                op, sub = num(m.group(1)), sub_key(m.group(2))
                key = (op, sub)
                if key in seen:
                    self.fail(f'{where}: MU_ROUTE(0x{op:02x}, {fmt_sub(sub)}) repeats {seen[key]}')
                    continue
                seen[key] = where
                routes.append({'op': op, 'sub': sub, 'addr': m.group(3), 'evidence': m.group(4), 'where': where})
                continue
            self.fail(f'{where}: not a MU_FAMILY or MU_ROUTE row: {text}')
        for r in routes:
            if r['sub'] != 'MU_SUB_NONE' and r['op'] not in families:
                self.fail(f'{r["where"]}: MU_ROUTE(0x{r["op"]:02x}, {fmt_sub(r["sub"])}) has a sub byte but no MU_FAMILY')
            if r['sub'] == 'MU_SUB_NONE' and r['op'] in families:
                self.fail(f'{r["where"]}: MU_ROUTE(0x{r["op"]:02x}, MU_SUB_NONE) for a sub-dispatched family')
        return families, routes

    def read_ignore(self):
        rows = []
        path = self.net / 'ignore.def'
        if not path.exists():
            return rows
        for line, text in strip_comments(path.read_text()):
            m = RE_IGNORE.match(text)
            if not m:
                self.fail(f'ignore.def:{line}: not a MU_IGNORE row: {text}')
                continue
            rows.append({'op': num(m.group(1)), 'sub': sub_key(m.group(2)), 'why': m.group(3),
                         'where': f'ignore.def:{line}'})
        return rows

    def read_ops(self, domains):
        ops, submits = [], []
        for d in domains:
            path = self.session / 'ops' / f'{d}.ops'
            for line, text in strip_comments(path.read_text()):
                where = f'ops/{d}.ops:{line}'
                m = RE_OP.match(text)
                if m:
                    ops.append({'op': num(m.group(1)), 'sub': sub_key(m.group(2)), 'fn': m.group(3),
                                'domain': d, 'where': where})
                    continue
                m = RE_SUBMIT.match(text)
                if m:
                    submits.append({'kind': m.group(1), 'fn': m.group(2), 'domain': d, 'where': where})
                    continue
                self.fail(f'{where}: not a MU_OP or MU_SUBMIT row: {text}')
        return ops, submits

    def read_intents(self, domains):
        kinds = []
        names, fields = {}, {}
        for path in sorted((self.session / 'domains').glob('*.intents')):
            d = path.stem
            if d not in domains:
                self.fail(f'domains/{path.name}: intents for a domain that is not one ({d})')
            for line, text in strip_comments(path.read_text()):
                where = f'domains/{path.name}:{line}'
                m = RE_KIND.match(text)
                if not m:
                    self.fail(f'{where}: not a MU_INTENT_KIND row: {text}')
                    continue
                name, field, ctype = m.group(1), m.group(2), m.group(3).strip()
                if name in names:
                    self.fail(f'{where}: intent kind {name} repeats {names[name]}')
                    continue
                if field in fields:
                    self.fail(f'{where}: payload field {field} repeats {fields[field]}')
                    continue
                names[name], fields[field] = where, where
                kinds.append({'name': name, 'field': field, 'type': ctype, 'domain': d, 'where': where})
        return kinds

    def read_behaviors(self):
        out = []
        d = self.fixture / 'behaviors'
        names = {}
        for path in sorted(d.glob('*.c')) if d.exists() else []:
            text = path.read_text()
            stem = path.stem
            m = re.search(r'const\s+mu_fixture_behavior\s+mu_fx_([A-Za-z0-9_]+)\s*=', text)
            n = re.search(r'\.name\s*=\s*"([^"]+)"', text)
            if not m or m.group(1) != stem:
                self.fail(f'behaviors/{path.name}: must define const mu_fixture_behavior mu_fx_{stem}')
                continue
            name = n.group(1) if n else stem
            if name in names:
                self.fail(f'behaviors/{path.name}: behaviour name "{name}" repeats {names[name]}')
                continue
            names[name] = f'behaviors/{path.name}'
            out.append({'symbol': stem, 'name': name})
        return out

    # ---- join -----------------------------------------------------------------------------------

    def join(self, families, routes, ignores, ops):
        table = {(r['op'], r['sub']): r for r in routes}
        bound, ignored = {}, {}
        for o in ops:
            key = (o['op'], o['sub'])
            if key not in table:
                self.fail(f'{o["where"]}: MU_OP(0x{o["op"]:02x}, {fmt_sub(o["sub"])}, {o["fn"]}) names no route in '
                          f'{self.routes_file.name}')
                continue
            if key in bound:
                self.fail(f'{o["where"]}: MU_OP(0x{o["op"]:02x}, {fmt_sub(o["sub"])}) binds a route already bound by '
                          f'{bound[key]["where"]} ({bound[key]["fn"]})')
            bound.setdefault(key, o)
        for i in ignores:
            key = (i['op'], i['sub'])
            if key not in table:
                self.fail(f'{i["where"]}: MU_IGNORE(0x{i["op"]:02x}, {fmt_sub(i["sub"])}) names no route')
                continue
            if key in bound:
                self.fail(f'{i["where"]}: MU_IGNORE and {bound[key]["where"]} share route '
                          f'(0x{i["op"]:02x}, {fmt_sub(i["sub"])})')
            if key in ignored:
                self.fail(f'{i["where"]}: MU_IGNORE repeats {ignored[key]["where"]}')
            ignored.setdefault(key, i)
        return table, bound, ignored

    def check_submits(self, kinds, submits):
        known = {'MU_INTENT_' + k['name'] for k in kinds}
        routed = {}
        for s in submits:
            if s['kind'] not in known:
                self.fail(f'{s["where"]}: MU_SUBMIT({s["kind"]}) names no intent kind')
                continue
            if s['kind'] in routed:
                self.fail(f'{s["where"]}: {s["kind"]} is already routed by {routed[s["kind"]]["where"]}')
                continue
            routed[s['kind']] = s
        for k in kinds:
            if 'MU_INTENT_' + k['name'] not in routed:
                self.fail(f'{k["where"]}: intent kind MU_INTENT_{k["name"]} has no MU_SUBMIT route')
        return routed

    # ---- outputs --------------------------------------------------------------------------------

    def write(self, out: Path, domains, families, routes, ignores, ops, kinds, submits, behaviors, bound, ignored,
              routed):
        out.mkdir(parents=True, exist_ok=True)
        head = '/* GENERATED by scripts/gen_domains.py - do not edit. */\n'
        files = {}
        files['session_domains.h'] = head + '#ifndef MU_SESSION_DOMAINS_H\n#define MU_SESSION_DOMAINS_H\n' + \
            'typedef enum mu_domain {\n' + ''.join(f'    MU_DOMAIN_{d.upper()},\n' for d in domains) + \
            '    MU_DOMAIN_COUNT\n} mu_domain;\n' + \
            '#define MU_DOMAIN_NAMES {' + ', '.join(f'"{d}"' for d in domains) + '}\n' + \
            ''.join(f'#include "domains/{d}.h"\n' for d in domains) + '#endif\n'
        files['domains_all.def'] = head + ''.join(f'MU_DOMAIN({d})\n' for d in domains)
        files['session_domains_state.h'] = head + '#ifndef MU_SESSION_DOMAINS_STATE_H\n' \
            '#define MU_SESSION_DOMAINS_STATE_H\n' + \
            ''.join(f'#include "domains/{d}_state.h"\n' for d in domains) + '#endif\n'
        files['ops_all.def'] = head + ''.join(f'#include "ops/{d}.ops"\n' for d in domains)
        rows = [head, f'/* route table: {self.rel(self.routes_file)} */\n']
        for op, f in sorted(families.items()):
            rows.append(f'MU_FAMILY(0x{op:02x}, {f["c1"]}, {f["c2"]}, {fmt_addr(f["addr"])})\n')
        for r in routes:
            rows.append(f'MU_ROUTE(0x{r["op"]:02x}, {fmt_sub(r["sub"])}, {fmt_addr(r["addr"])}, {r["evidence"]})\n')
        files['routes.def'] = ''.join(rows)
        rows = [head, '/* MU_BOUND(op, sub, client_handler, apply) one per MU_OP row (a repeated row repeats a case);\n'
                ' * MU_IGNORED(op, sub, client_handler, why); MU_UNBOUND(op, sub, client_handler) */\n']
        table = {(r['op'], r['sub']): r for r in routes}
        for o in ops:
            r = table.get((o['op'], o['sub']))
            addr = fmt_addr(r['addr']) if r else 'MU_ADDR_UNVERIFIED'
            rows.append(f'MU_BOUND(0x{o["op"]:02x}, {fmt_sub(o["sub"])}, {addr}, {o["fn"]})\n')
        for i in ignores:
            r = table.get((i['op'], i['sub']))
            addr = fmt_addr(r['addr']) if r else 'MU_ADDR_UNVERIFIED'
            if (i['op'], i['sub']) not in bound:
                rows.append(f'MU_IGNORED(0x{i["op"]:02x}, {fmt_sub(i["sub"])}, {addr}, {i["why"]})\n')
        for r in routes:
            key = (r['op'], r['sub'])
            if key not in bound and key not in ignored:
                rows.append(f'MU_UNBOUND(0x{r["op"]:02x}, {fmt_sub(r["sub"])}, {fmt_addr(r["addr"])})\n')
        files['bound_routes.def'] = ''.join(rows)
        kind_rows = ''.join(f'    MU_INTENT_{k["name"]},\n' for k in kinds)
        payload = '    uint8_t none_; \\\n' + ''.join(f'    {k["type"]} {k["field"]}; \\\n' for k in kinds)
        files['session_intents.h'] = head + '#ifndef MU_SESSION_INTENTS_H\n#define MU_SESSION_INTENTS_H\n' + \
            'typedef enum mu_intent_kind {\n    MU_INTENT_NONE = 0,\n' + kind_rows + '    MU_INTENT_KINDS\n} mu_intent_kind;\n' + \
            '/* the payload union members, one per kind (domains/<d>.intents) */\n#define MU_INTENT_PAYLOADS \\\n' + \
            payload + '    /* end */\n' + \
            '#define MU_INTENT_KIND_NAMES {"none", ' + ', '.join(f'"{k["field"]}"' for k in kinds) + '}\n#endif\n'
        files['fixture_behaviors.def'] = head + ''.join(f'MU_FX_BEHAVIOR({b["symbol"]})\n' for b in behaviors)
        summary = {
            'route_table': self.rel(self.routes_file),
            'domains': domains,
            'routes': [{'opcode': r['op'], 'sub': None if r['sub'] == 'MU_SUB_NONE' else r['sub'],
                        'client_handler': None if r['addr'] == 'MU_ADDR_UNVERIFIED' else num(r['addr']),
                        'evidence': r['evidence'],
                        'apply': bound[(r['op'], r['sub'])]['fn'] if (r['op'], r['sub']) in bound else None,
                        'ignored': (r['op'], r['sub']) in ignored} for r in routes],
            'intents': [{'kind': 'MU_INTENT_' + k['name'], 'domain': k['domain'],
                         'submit': routed['MU_INTENT_' + k['name']]['fn'] if 'MU_INTENT_' + k['name'] in routed
                         else None} for k in kinds],
            'behaviors': [b['name'] for b in behaviors],
        }
        files['gen_domains.json'] = json.dumps(summary, indent=1) + '\n'
        for name, text in files.items():
            path = out / name
            if not path.exists() or path.read_text() != text:   # unchanged files keep their mtime
                path.write_text(text)

    def run(self, out: Path, checks: bool) -> int:
        domains = self.read_domains()
        families, routes = self.read_table()
        ignores = self.read_ignore()
        ops, submits = self.read_ops(domains)
        kinds = self.read_intents(domains)
        behaviors = self.read_behaviors()
        _, bound, ignored = self.join(families, routes, ignores, ops)
        routed = self.check_submits(kinds, submits)
        if self.errors:
            for e in self.errors:
                print(f'gen_domains: {e}', file=sys.stderr)
            if checks:
                print(f'gen_domains: {len(self.errors)} rule violation(s); nothing written', file=sys.stderr)
                return 1
        self.write(out, domains, families, routes, ignores, ops, kinds, submits, behaviors, bound, ignored, routed)
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--session', type=Path, default=ROOT / 'native/session')
    ap.add_argument('--net', type=Path, default=ROOT / 'native/net')
    ap.add_argument('--fixture', type=Path, default=ROOT / 'native/fixture')
    ap.add_argument('--routes', type=Path, help='route table (default: net/dispatch.def, else net/dispatch.seed.def)')
    ap.add_argument('--out', type=Path, default=ROOT / 'native/build/gen')
    ap.add_argument('--no-checks', action='store_true', help='negative build test only: write despite violations')
    args = ap.parse_args()
    return Gen(args.session, args.net, args.fixture, args.routes).run(args.out, not args.no_checks)


if __name__ == '__main__':
    sys.exit(main())
