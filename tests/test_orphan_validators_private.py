"""Private runs of the validators that no older test ran (VERIFY-HARNESS-001).

Every scripts/validators.toml row whose owning test is this file gets one test method here,
OrphanValidators.test_<name>. It runs the row exactly as scripts/run_validators.py does (the row's pinned
inputs, arguments and report expectations) and fails on a mismatch, a missed planted mistake or an
unexpected count.

Skips without MU_RECOVERY_INTEGRATION=1, like the other private suites. With it, a missing restored text
or second image section is an error (the integration run was requested without its core captures); a row
whose other inputs are absent (a langread snapshot without MU_SNAPSHOT_DIR, the installed client without
MU_GAME_ROOT, a compiler) skips and names what is missing.
"""
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_validators as rv  # noqa: E402

HERE = 'tests/test_orphan_validators_private.py'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
CORE = {'text', 'data'}


@unittest.skipUnless(PRIVATE, 'private client comparisons need MU_RECOVERY_INTEGRATION=1')
class OrphanValidators(unittest.TestCase):
    maxDiff = None

    def run_manifest_row(self, name):
        row = rv.load_manifest()[name]
        entry = rv.run_row(name, row)
        if entry['status'] == 'skip':
            missing_core = CORE & set(entry.get('missing_pins', []))
            if missing_core:
                self.fail(f'{name}: integration requested without {sorted(missing_core)}: {entry["reason"]}')
            self.skipTest(f'{name}: {entry["reason"]}')
        failed = {k: v for k, v in entry.get('expect', {}).items() if not v['ok']}
        self.assertEqual(entry['status'], 'pass',
                         f'{name}: {entry.get("reason", "")}\n{json.dumps(failed, indent=1, default=str)[:4000]}')
        for key in ('cases', 'mutants'):
            if row.get(key) is not None and key in entry:
                self.assertEqual(entry[key], row[key], f'{name}: {key}')


def _add_tests():
    for name, row in rv.load_manifest().items():
        test = row.get('test', '')
        if not test.startswith(HERE + '::OrphanValidators.'):
            continue
        method = test.rsplit('.', 1)[1]

        def check(self, name=name):
            self.run_manifest_row(name)
        check.__name__ = method
        check.__doc__ = f'{name} against the client ({row.get("note", "manifest row")[:80]})'
        setattr(OrphanValidators, method, check)


_add_tests()


if __name__ == '__main__':
    unittest.main()
