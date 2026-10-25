"""The include audit (SESSION-CORE-001): wire and session-internal types stay inside native/net,
native/session and native/fixture (scripts/audit_includes.py, rules in its docstring and in
docs/design/native-port/sketch/MODULES.md). The repository passes; planted violations in a temporary
tree are each reported, and allowed includes are not."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
AUDIT = ROOT / 'scripts/audit_includes.py'


def audit(root):
    return subprocess.run([sys.executable, str(AUDIT), '--root', str(root)], capture_output=True, text=True)


def write(root, rel, text=''):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class IncludeAudit(unittest.TestCase):
    def test_repository_passes(self):
        r = audit(ROOT)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_planted_violations_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in ('native/net/mu_link.h', 'native/net/mu_conn.h', 'native/net/mu_transport.h',
                        'native/core/mu_protocol.h', 'native/session/session_internal.h',
                        'native/session/mu_session.h', 'native/session/domains/hero_state.h',
                        'native/fixture/behavior.h', 'native/fixture/mu_fixture.h'):
                write(tmp, rel, '/* stand-in */\n')
            # violations: a world part reaching a link, a GFx window reaching session internals and a domain's
            # state, a client file reaching the wire protocol header and a fixture-internal header by name
            write(tmp, 'native/world/parts/bad.c', '#include "../../net/mu_link.h"\n')
            write(tmp, 'native/gfx/windows/bad.c', '#include "../../session/session_internal.h"\n'
                                                   '#include "../../session/domains/hero_state.h"\n')
            write(tmp, 'native/client/bad.c', '#include "../core/mu_protocol.h"\n#include "behavior.h"\n'
                                              '#include "ops_all.def"\n')
            # allowed: public headers from anywhere, private ones inside their modules
            write(tmp, 'native/world/ok.c', '#include "../session/mu_session.h"\n#include "../net/mu_transport.h"\n'
                                            '#include "../fixture/mu_fixture.h"\n')
            write(tmp, 'native/session/ok.c', '#include "session_internal.h"\n#include "../net/mu_conn.h"\n')
            write(tmp, 'native/fixture/ok.c', '#include "behavior.h"\n#include "../net/mu_link.h"\n')
            r = audit(tmp)
            self.assertEqual(r.returncode, 1)
            lines = [l for l in r.stderr.splitlines() if ': includes ' in l]
            self.assertEqual(len(lines), 6, r.stderr)
            for where in ('native/world/parts/bad.c:1', 'native/gfx/windows/bad.c:1', 'native/gfx/windows/bad.c:2',
                          'native/client/bad.c:1', 'native/client/bad.c:2', 'native/client/bad.c:3'):
                self.assertTrue(any(l.startswith(where + ':') for l in lines), where)
            self.assertFalse(any('/ok.c' in l for l in lines))


if __name__ == '__main__':
    unittest.main()
