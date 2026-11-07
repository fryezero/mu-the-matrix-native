"""RENDER-EFFECTS-017: portable native routes; pinned instruction comparisons run separately."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]


def build_host(tmp, raster=None):
    """effects17_host.c against the native libraries (scripts/validate_render_effects17.py builds it the same way);
    raster: a mutated copy of mu_raster.c compiled in place of the library's."""
    native = ROOT/'native'
    subprocess.run(['make', '-s', '-C', str(native), 'build/libmunative.a', 'build/libmusession_world.a'],
                   check=True, capture_output=True)
    host, obj, source = Path(tmp)/'host', Path(tmp)/'host.o', native/'tests/effects17_host.c'
    if raster is not None:
        source = Path(tmp)/'effects17_host.c'
        source.write_text((native/'tests/effects17_host.c').read_text().replace(
            '#include "../core/mu_raster.c"', f'#include "{raster}"'))
    command = ['clang', '-std=c11', '-O2', '-ffp-contract=off', '-I', str(native/'build/gen'), '-I', str(native/'session'),
               '-iquote', str(native/'core'), '-c', str(source), '-o', str(obj)]
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    command = ['clang++', str(obj), str(native/'build/libmunative.a'), str(native/'build/libmusession_world.a'), '-lm',
               '-o', str(host)]
    if sys.platform == 'darwin':
        command += ['-L/opt/homebrew/opt/cryptopp/lib', '-lcryptopp', '-L/opt/homebrew/opt/jpeg-turbo/lib', '-ljpeg',
                    '-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation']
    else:
        command += ['-lcryptopp', '-ljpeg']
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr)
    return host


class Native(unittest.TestCase):
    def test_armour_particle_kinds_and_raster_clamp_to_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = build_host(tmp)
            p = subprocess.run([str(host)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("armour particle kinds 0x810a/7, 0x810a/0xf, 0x7f26/0x26 and the raster's clamp to edge "
                          'through native routes: OK', p.stdout)
            # a 4-texel ramp: the outer half texels of GL_CLAMP keep the edge texel, GL_REPEAT blends the far edge
            ramp = '000000ff' + '555555ff' + 'aaaaaaff' + 'ffffffff'
            lines = [f'4 1 2900 2601 3d800000 3f000000 {ramp}',    # s = 0.0625: inside the first half texel
                     f'4 1 2901 2601 3d800000 3f000000 {ramp}',
                     f'4 1 2900 2601 3f700000 3f000000 {ramp}']    # s = 0.9375: the last half texel
            out = subprocess.run([str(host), 'sample'], input='\n'.join(lines) + '\n', capture_output=True, text=True,
                                 check=True).stdout.split('\n')
        self.assertEqual(out[0].split()[0], '00000000')
        self.assertEqual(out[1].split()[0], '3e800000')   # a quarter of the far white texel
        self.assertEqual(out[2].split()[0], '3f800000')


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects17.py'),
                            '--cases', '20', '--mutations', '--output', str(out)], check=True, capture_output=True)
            report = json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertTrue(report['all_mutants_caught'])
        self.assertEqual(report['instruction_cases'], CASES)
        self.assertEqual(len(report['mutants']), MUTANTS)


CASES, MUTANTS = 618, 20   # the registry row (scripts/validators.toml)


if __name__ == '__main__':
    unittest.main()
