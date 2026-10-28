"""Compile three intentional mistakes and require the portable oracle tests to fail.
All altered source, objects and logs go to a new external scratch directory.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scratch', type=Path, required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    native = here.parent
    if args.scratch.resolve().is_relative_to(native.parent):
        ap.error('scratch must be outside the repository')
    args.scratch.mkdir(parents=True, exist_ok=False)
    subprocess.run(['make', '-C', str(here), 'converter'], check=True, capture_output=True)
    libflags = []
    if sys.platform == 'darwin':
        prefix = subprocess.check_output(['brew', '--prefix', 'cryptopp'], text=True).strip()
        libflags = ['-L' + prefix + '/lib']
    mutations = [
        ('premultiply', 'gfxconvert_image.c', 'im.px[i + (size_t)c] * a / 255',
         'im.px[i + (size_t)c] * a / 256', 'test_dxt1_dxt3_dxt5_and_bilinear_alpha'),
        ('font-subset', 'gfxconvert_fonts.c', 'c <= 0x24f', 'c <= 0x4e00', 'test_default_and_app_options'),
        ('bridge', 'gfxconvert_actions.c', '"__mu_get"', '"__mu_bad"', 'test_bridge_and_initial_value_types'),
    ]
    for name, source, old, new, test in mutations:
        folder = args.scratch / name
        folder.mkdir()
        text = (here / source).read_text()
        assert text.count(old) == 1
        mutant = folder / source
        mutant.write_text(text.replace(old, new))
        obj = folder / (Path(source).stem + '.o')
        subprocess.run(['clang', '-std=c11', '-O2', '-ffp-contract=off', '-I', str(here), '-c', str(mutant),
                        '-o', str(obj)], check=True, capture_output=True)
        objects = [p for p in sorted((native / 'build/gfxconvert').glob('*.o')) if p.name != obj.name]
        binary = folder / 'gfxconvert'
        subprocess.run(['clang++', str(obj), *map(str, objects), *libflags, '-lcryptopp', '-lz',
                        '-o', str(binary)], check=True, capture_output=True)
        env = dict(os.environ, MU_GFXCONVERT_TEST_BINARY=str(binary))
        r = subprocess.run([sys.executable, '-m', 'unittest', f'test_gfxconvert_c.ConverterC.{test}'],
                           cwd=native / 'tests', env=env, capture_output=True, text=True)
        (folder / 'test.log').write_text(r.stdout + r.stderr)
        if r.returncode == 0 or 'FAIL:' not in r.stderr:
            raise AssertionError(f'{name}: mutant was not caught by an assertion')
        print(f'{name}: caught')
    print('3/3 planted mistakes caught')


if __name__ == '__main__':
    main()
