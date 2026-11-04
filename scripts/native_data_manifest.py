"""Native Data export provenance. The C++ engine also runs inside the app.

Raw outputs are for authored fixtures/research only; setup never imports them.
A main.exe pin associates an offline snapshot with the supported build. It does
not independently attest which process produced an old snapshot.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'native/build/mu-native-data'


def arguments(parser):
    parser.add_argument('--main-exe', type=Path, default=ROOT / 'input/main.exe',
                        help='supported client executable, hashed for Native Data provenance')
    parser.add_argument('--raw-output', action='store_true',
                        help='unversioned research/fixture output; cannot be imported by app setup')


def run(*args):
    if not TOOL.is_file():
        raise SystemExit('Build the manifest helper first: make -C native build/mu-native-data')
    result = subprocess.run([str(TOOL), *map(str, args)], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stderr.strip())


def prepare(args):
    if not args.raw_output:
        run('pin', args.main_exe)


def prepare_output(args, directory):
    if args.raw_output:
        return
    directory = Path(directory)
    if directory.exists() and any(directory.iterdir()):
        run('check', directory, args.main_exe)


def publish(args, directory, producer, inputs):
    if not args.raw_output:
        run('write', directory, args.main_exe, producer, *inputs)


def producer(directory):
    """The producer line of a published export, or None when the directory has no manifest."""
    path = Path(directory) / 'native-data.manifest'
    if not path.is_file():
        return None
    for line in path.read_text(encoding='ascii').splitlines()[:3]:
        if line.startswith('producer '):
            return line[len('producer '):]
    raise SystemExit(f'{path}: no producer line')


def publish_step(main_exe, directory, step, inputs):
    """Record a later step's outputs in an already published export (NATIVE-DATA-MANIFEST-001).

    Check the export (run('check', ...)) before the step writes its outputs. The engine keeps the earlier
    input provenance; the producer names every step in order (lang-export-v1-effects-v1-mapanim-v1-...)."""
    previous = producer(directory)
    if previous is None:
        raise SystemExit(f'{directory}: a later step needs a published export')
    run('write', directory, main_exe, f'{previous}-{step}', *inputs)
