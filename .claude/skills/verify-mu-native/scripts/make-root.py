#!/usr/bin/env python3
"""Write the synthetic game root and offline session that verify-mu-native drives.

    tools/python/bin/python .claude/skills/verify-mu-native/scripts/make-root.py RUN_DIR

Creates RUN_DIR/root with
  Data/World1             flat open ground, a safe-zone strip at y 100..110 and a wall line at y 150
                          (the walk-around world; the tools call it --world 0)
  Data/World94            the character-select world
  Data/World95            the login backdrop world (the client's 0x5e)
  Data/Player/Player.bmd  a 50-bone, 0x60-action skeleton in the v15 envelope; it has no meshes, so a
                          model view of it alone shows only the background
  Data/Interface/New_lo_webzen_logo.OZT      the title logo
  Data/Verify/synthetic1_v12.bmd + 3 OZT     a 3-mesh, 7-bone textured model for the model viewer
and RUN_DIR/session.txt (+ servers.txt, characters.txt): servers S-1 (open), S-closed, S-3; characters
Alpha (slot 0, class 0x00), Bravo (slot 1, class 0x22), Charlie (slot 2, class 0x03); joins slot 0 ->
world 0 at tile 120,120 and slot 1 -> world 0 at 128,128 facing 90.

Every byte is authored by the fixtures in native/tests; nothing comes from the installed client.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'native' / 'tests'))

import native_fixtures as nf  # noqa: E402
from test_native_shell import write_root, write_session  # noqa: E402
from test_native_terrain import write_world  # noqa: E402


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    run = pathlib.Path(argv[1]).resolve()
    run.mkdir(parents=True, exist_ok=True)
    root = run / 'root'
    write_root(root)
    write_world(root, folder=95)
    verify = root / 'Data' / 'Verify'
    verify.mkdir(parents=True, exist_ok=True)
    model = nf.write_textured_model(verify, seed=1, version=12)
    session = write_session(run)
    print(f'root={root}')
    print(f'session={session}')
    print(f'model={model}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
