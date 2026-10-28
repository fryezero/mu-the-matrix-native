"""Fresh core targets must generate their session headers before compiling."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('make'), 'make is required for the native build')
class BuildGenerationTests(unittest.TestCase):
    def test_fresh_session_consumers_generate_headers_first(self):
        # Combat and NPCs include session headers directly or through the quest facade.
        for source in ('mu_combat', 'mu_npc', 'mu_world_players'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as folder:
                build = Path(folder) / 'build'
                result = subprocess.run(['make', '-n', f'BUILD={build}', str(build / f'core/{source}.o')],
                                        cwd=NATIVE, check=True, capture_output=True, text=True)
                plan = result.stdout
                compile_at = plan.index(f'-c core/{source}.c')
                self.assertIn('gen_domains.py --out', plan)
                self.assertIn('gen_layout.py --out', plan)
                self.assertLess(plan.index('gen_domains.py --out'), compile_at)
                self.assertLess(plan.index('gen_layout.py --out'), compile_at)
