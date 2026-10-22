"""The pet process in the walk-around world (NATIVE-HELPERS-002) checks.

Portable (synthetic data only), through `mu-walk` (headless, software
rasterizer) on the synthetic combat world of test_native_combat.py with
synthetic pet models (Data/Item/demon.bmd, pandapet.bmd, skeletonpet.bmd,
xmas_deer.bmd) and a synthetic Data/Local/petdata.bmd written with the
client's record XOR and checksum:
  * --helper demon: CreatePet makes one pet that flies 230 above its owner
    (move type 0) and is drawn; its visuals create sprites and particles;
  * --helper panda: the collector (move type 1) stays 20 above the ground and
    follows the hero (state 0, no ground items offered: DEMO);
  * the record's scale reaches the pet (Create's 0x00eb0953);
  * without petdata.bmd the module falls back to its built-in records;
  * demo players with pet=skeleton / pet=rudolph: ChangeCharacterExt's
    CreatePet calls give them their pets (owners 1 and 2).
The comparison with the client's routines is scripts/validate_pets.py.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
import native_fixtures as nf  # noqa: E402
from test_native_combat import write_combat_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
BUX = (0xfc, 0xcf, 0xab)


def checksum(data, key=0x3bb2):
    s = (key << 9) & 0xffffffff
    for i in range(0, len(data) - 3, 4):
        word = struct.unpack('<I', data[i:i + 4])[0]
        s = (s ^ word) if ((i >> 2) + key) % 2 == 0 else (s + word) & 0xffffffff
        if i % 16 == 0:
            s ^= ((key + s) & 0xffffffff) >> (((i >> 2) % 8) + 1)
    return s


def petdata(records):
    """records: (item index, move, range, follow, scale, blend mesh)."""
    raw = bytearray(0x600)
    for n, (item, move, rng, follow, scale, blend) in enumerate(records):
        rec = struct.pack('<ii4Bf4Bfi5f', n, item, 0xff, 0, 8, move, rng, follow, 0, 0, 0, scale, blend, *[0.5]*5)
        raw[n*0x30:(n+1)*0x30] = bytes(b ^ BUX[i % 3] for i, b in enumerate(rec))
    for n in range(len(records), 32):
        raw[n*0x30:(n+1)*0x30] = bytes(BUX[i % 3] for i in range(0x30))   # a zero record after BuxConvert
    return bytes(raw) + struct.pack('<I', checksum(bytes(raw)))


def write_pet_models(root, with_data=True):
    item = Path(root)/'Data'/'Item'
    item.mkdir(parents=True, exist_ok=True)
    for name, seed in (('demon', 41), ('pandapet', 42), ('skeletonpet', 43), ('xmas_deer', 44)):
        path = nf.write_textured_model(item, seed)
        path.rename(item/f'{name}.bmd')
    local = Path(root)/'Data'/'Local'
    local.mkdir(parents=True, exist_ok=True)
    if with_data:
        (local/'petdata.bmd').write_bytes(petdata([(0x40, 0, 50.0, 1, 0.25, -1), (0x43, 1, 10.0, 0, 0.8, -1),
                                                   (0x50, 1, 10.0, 0, 0.75, -1), (0x7b, 1, 10.0, 0, 0.5, -1)]))


def run(root, *args, size=(64, 64), tile='120,120', check=True):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio',
                                 '--no-env', '--width', str(size[0]), '--height', str(size[1]),
                                 '--every', '1', '--out-dir', tmp, '--tile', tile, *[str(a) for a in args]],
                                capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'pets': [r for r in rows if 'pets_frame' in r],
            'walk': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r['pets'] for r in rows if isinstance(r.get('pets'), dict)), None),
            'logs': [line for line in result.stdout.splitlines() if line.startswith('helpers: ')],
            'returncode': result.returncode, 'stderr': result.stderr}


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_combat_world(Path(cls.tmp.name)/'game')
        write_pet_models(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class HeroPets(Build):
    def test_demon_flies_above_the_hero(self):
        out = run(self.root, '--frames', '60', '--helper', 'demon')
        s = out['summary']
        self.assertEqual((s['petdata'], s['created'], s['live']), (0, 1, 1))
        last = out['pets'][-1]
        pet = last['pet0']
        self.assertEqual(pet[:3], [0x1a40, 0, 0])                 # Demon, owner 0 (the hero), state 0
        hero = out['walk'][-1]['hero']
        self.assertAlmostEqual(pet[5], hero[2] + 230.0, places=1)  # 230 * the owner scale above it
        self.assertLess(abs(pet[3] - hero[0]) + abs(pet[4] - hero[1]), 300)
        self.assertGreater(sum(f['drawn'] for f in out['pets']), 0)
        self.assertGreater(s['sprites'], 0)                       # lightmarks / flare sprites at its bones
        self.assertGreater(s['particles'], 0)                     # Clud64 (0x7ffd) and firehik03 (0x8085)
        self.assertTrue(any('model 0x2526: Data/Item/demon.bmd' in line for line in out['logs']))

    def test_panda_follows_on_the_ground(self):
        out = run(self.root, '--frames', '80', '--helper', 'panda', '--walk', '124,120')
        pet = out['pets'][-1]['pet0']
        self.assertEqual(pet[:2], [0x1a50, 0])
        self.assertIn(pet[2], (0, 3))                             # following (no zen offered)
        hero = out['walk'][-1]['hero']
        self.assertAlmostEqual(pet[5], hero[2] + 20.0, delta=1.0)  # owner z + 20
        moves = {tuple(f['pet0'][3:5]) for f in out['pets']}
        self.assertGreater(len(moves), 5)                         # it walks after the hero

    def test_without_petdata_the_builtin_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_combat_world(Path(tmp)/'game')
            write_pet_models(root, with_data=False)
            out = run(root, '--frames', '10', '--helper', 'skeleton')
        self.assertEqual(out['summary']['petdata'], 1)            # missing file
        self.assertEqual(out['summary']['created'], 1)

    def test_unknown_and_off(self):
        out = run(self.root, '--frames', '5', '--helper', 'demon', '--no-helpers')
        self.assertEqual(out['pets'], [])


class PlayerPets(Build):
    def test_players_get_their_pets(self):
        players = Path(self.tmp.name)/'players.txt'
        players.write_text('player Aeris class=0x01 at=123,120 dir=3 pk=3 level=180 pet=skeleton idle=5\n'
                           'player Kyra class=0x02 at=118,122 dir=1 pk=3 level=200 pet=rudolph '
                           'route=118,126;118,122 idle=5\n')
        out = run(self.root, '--frames', '100', '--players', players)
        s = out['summary']
        self.assertEqual(s['created'], 2)
        last = out['pets'][-1]
        owners = sorted((last[k][0], last[k][1]) for k in ('pet0', 'pet1'))
        self.assertEqual(owners, [(0x1a43, 2), (0x1a7b, 1)])     # Rudolph with Kyra, the Skeleton with Aeris
        self.assertTrue(all(last[k][2] == 4 for k in ('pet0', 'pet1')))   # not the hero's: state 4


@unittest.skipUnless(PRIVATE, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateTests(unittest.TestCase):
    def test_lorencia_pets(self):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        for name, item, model in (('demon', 0x1a40, 'demon.bmd'), ('spirit', 0x1a41, 'maria.bmd'),
                                  ('rudolph', 0x1a43, 'xmas_deer.bmd'), ('unicorn', 0x1a6a, 'pet_unicorn.bmd')):
            out = run(os.environ['MU_GAME_ROOT'], '--frames', '40', '--helper', name, size=(320, 240),
                      tile='133,127')
            self.assertEqual(out['summary']['petdata'], 0)        # the installed petdata.bmd
            self.assertEqual(out['pets'][-1]['pet0'][0], item)
            self.assertTrue(any(model in line and '(0 textures missing)' in line for line in out['logs']), name)


if __name__ == '__main__':
    unittest.main()
