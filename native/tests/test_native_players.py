"""Other players in the walk-around world (NATIVE-PLAYERS-001) checks.

Portable (synthetic data only), through `mu-walk` (headless, software
rasterizer) on the synthetic combat world of test_native_combat.py with a
demo players file:
  * the demo server's viewport creates the players within range on the first
    step (keys 0x200.., class parts from the code 0x1ff, addInfo plates of
    kind 1 with the PK colour and the guild line);
  * the move packets start walks through the client path finder; the remote
    step moves the players (MovePath / MoveCharacterPosition) to the route's
    tiles, the walk action while moving and the stand action on arrival;
  * a player beyond the demo range is not created; walking the hero toward it
    creates it (viewport), walking away destroys it (removeInfo);
  * the scripted die packet: SetPlayerDie's Player action, the dead fade and
    the removal of the plate, the demo respawn;
  * the store packet: setStore on the plate; --no-players and determinism.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): Lorencia with the demo
players (item parts from Item.bmd, the walk-in / destroy round trip).
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_combat import write_combat_world  # noqa: E402

WALK = NATIVE/'build/mu-walk'
PLAYERS = NATIVE/'world/lorencia-demo-players.txt'
PLACEMENT = NATIVE/'world/lorencia-demo-placement.txt'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
KEY0 = 0x200


def run(root, players, *args, size=(64, 64), tile='120,120'):
    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', '--no-audio',
                                 '--no-env', '--no-particles', '--width', str(size[0]), '--height', str(size[1]),
                                 '--every', '1', '--out-dir', tmp, '--tile', tile, '--players', str(players),
                                 *[str(a) for a in args]], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    return {'frames': [r for r in rows if 'players_frame' in r],
            'names': [r for r in rows if 'names_frame' in r],
            'walk': [r for r in rows if 'frame' in r and 'tick' in r],
            'summary': next((r['players'] for r in rows if 'players' in r and isinstance(r['players'], dict)), None),
            'players': [r for r in rows if 'player' in r and 'parts' in r],
            'logs': [r['players_log'] for r in rows if 'players_log' in r],
            'plates': [r for r in rows if 'plate' in r], 'stdout': result.stdout}


def player(frame, key):
    return next(p for p in frame['players'] if p[0] == key)


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = write_combat_world(Path(cls.tmp.name)/'game')
        cls.players = Path(cls.tmp.name)/'players.txt'
        cls.players.write_text(
            '# demo\n'
            'player Aeris class=0x01 at=123,120 dir=3 pk=5 level=180 guild=0 party route=126,120;123,123 idle=5\n'
            'player Farboy class=0x02 at=150,150 dir=1 pk=3 level=10 route=152,150 idle=5\n'
            'player Doomed class=0x00 at=118,122 dir=2 pk=3 level=50 die=20 respawn=60\n'
            'player Seller class=0x04 at=120,117 dir=0 pk=0 level=400 store=10 title=Cheap_stuff\n')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()


class PlayersTests(Build):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.out = run(cls.root, cls.players, '--frames', '200')

    def test_viewport_creates_the_players_in_range(self):
        first = self.out['frames'][0]
        self.assertEqual([p[1] for p in first['players']], [1, 0, 1, 1])   # Farboy at 150,150 is beyond the range
        self.assertGreaterEqual(self.out['summary']['viewport_packets'], 3)   # three now, Doomed again after the respawn
        self.assertGreaterEqual(self.out['summary']['addinfo'], 3)
        aeris = next(p for p in self.out['players'] if p['name'] == 'Aeris')
        self.assertEqual(aeris['class'], 1)
        self.assertEqual(aeris['pk'], 5)
        # class parts (code 0x1ff): 0x3700 + skin index per slot, no weapons
        self.assertEqual([t for t, *_ in aeris['parts'][1:6]], [0x3701, 0x3751, 0x37a1, 0x37f1, 0x3841])
        self.assertEqual(aeris['parts'][6][0], -1)

    def test_plates_show_players_with_pk_colour_guild_and_party_bar(self):
        plates = self.out['names'][0]['plates']
        aeris = next(p for p in plates if p[0] == KEY0)
        self.assertEqual(aeris[1], 1)            # kind 1 (player)
        self.assertEqual(aeris[7], 1)            # the party member's HP bar
        summary = self.out['plates']
        keys = sorted(p['plate'] for p in summary if p['type'] == 1)
        self.assertEqual(keys, [KEY0, KEY0 + 2, KEY0 + 3, 0x1234])   # three players and the hero, all kind 1

    def test_move_packets_walk_the_route(self):
        frames = self.out['frames']
        start = player(frames[0], KEY0)
        self.assertEqual((start[5], start[6]), (123, 120))
        moving = [player(f, KEY0) for f in frames if player(f, KEY0)[8] == 1]
        self.assertGreater(len(moving), 10)
        self.assertTrue(all(p[7] in (0x32, 0x33, 0x4f, 0x63) for p in moving))   # SetPlayerWalk's walk / run actions
        tiles = {(player(f, KEY0)[5], player(f, KEY0)[6]) for f in frames}
        self.assertIn((126, 120), tiles)
        self.assertGreaterEqual(self.out['summary']['move_packets'], 2)
        self.assertGreaterEqual(self.out['summary']['path_calls'], 2)
        aeris = next(p for p in self.out['players'] if p['name'] == 'Aeris')
        self.assertGreaterEqual(aeris['arrivals'], 1)
        standing = [player(f, KEY0) for f in frames if player(f, KEY0)[8] == 0]
        self.assertTrue(all(p[7] == 1 for p in standing))                         # the class-1 stand action

    def test_die_packet_fade_and_respawn(self):
        frames = self.out['frames']
        doomed = [player(f, KEY0 + 2) for f in frames]
        dead = [p for p in doomed if p[9] > 0]
        self.assertTrue(dead)
        # SetPlayerDie runs from the dead counter 15 on: the Player die actions
        self.assertTrue(any(p[7] in (0x142, 0x144, 0x145, 0x146, 0x147) for p in dead))
        self.assertTrue(any(p[10] < 1.0 for p in dead))                   # the dead fade
        removed = [i for i, p in enumerate(doomed) if p[1] == 0]
        self.assertTrue(removed)
        self.assertEqual(self.out['summary']['die_packets'], 1)
        self.assertGreaterEqual(self.out['summary']['removeinfo'], 1)
        self.assertTrue(any('removed after the dead fade' in l for l in self.out['logs']))
        later = [p for p in doomed[removed[0]:] if p[1] == 1 and p[9] == 0]
        self.assertTrue(later, 'the demo respawn creates the player again')

    def test_store_packet(self):
        frames = self.out['frames']
        seller = [player(f, KEY0 + 3) for f in frames]
        self.assertEqual(seller[0][11], 0)
        self.assertTrue(any(p[11] == 1 for p in seller))
        self.assertEqual(self.out['summary']['store_packets'], 1)
        self.assertTrue(any("opens 'Cheap stuff'" in l for l in self.out['logs']))

    def test_runs_are_deterministic(self):
        again = run(self.root, self.players, '--frames', '200')
        self.assertEqual([f['players'] for f in again['frames']], [f['players'] for f in self.out['frames']])


class RangeTests(Build):
    def test_walking_into_range_creates(self):
        # the hero's long-distance auto move toward Farboy (150,150): the demo viewport creates him
        out = run(self.root, self.players, '--frames', '400', '--auto-move', '140,140')
        far = [player(f, KEY0 + 1) for f in out['frames']]
        self.assertEqual(far[0][1], 0)
        self.assertTrue(any(p[1] == 1 for p in far), 'the hero came within range')
        self.assertTrue(any(l.startswith('viewport: Farboy') for l in out['logs']))
        self.assertTrue(any(l.endswith('(walks in)') for l in out['logs']))

    def test_walking_out_of_range_destroys(self):
        # starting next to Farboy, the hero walks away: the destroy packet, removeInfo
        out = run(self.root, self.players, '--frames', '500', '--auto-move', '118,118', tile='142,142')
        far = [player(f, KEY0 + 1) for f in out['frames']]
        self.assertEqual(far[0][1], 1)
        self.assertTrue(any(p[1] == 0 for p in far), 'destroyed when the hero left')
        self.assertGreaterEqual(out['summary']['destroy_packets'], 1)
        self.assertGreaterEqual(out['summary']['removeinfo'], 1)
        self.assertTrue(any(l.startswith('destroy: Farboy') for l in out['logs']))

    def test_no_players(self):
        out = run(self.root, self.players, '--frames', '3', '--no-players')
        self.assertEqual(out['frames'], [])
        self.assertIsNone(out['summary'])


class ArmourTexturesTests(Build):
    def test_player_folder_fallback_keeps_effect_textures(self):
        import io
        import native_fixtures as nf
        from test_native_data import item_file, item_record
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(write_combat_world(Path(tmp)/'game'))
            item = root/'Data/Item'
            item.mkdir()
            model = nf.write_textured_model(root/'Data/Player', 7)
            (item/'HelmMale10.bmd').write_bytes(model.read_bytes())
            local = root/'Data/Local'
            local.mkdir(exist_ok=True)
            rec = bytearray(item_record(7*512+9, b'Data\\Item\\', b'HelmMale10.bmd', b'Demo helm'))
            rec[0x250:0x253] = bytes(3)
            (local/'item.bmd').write_bytes(item_file([bytes(rec)]))
            effects = root/'Data/Effect'
            effects.mkdir(exist_ok=True)
            for name in ('Chrome02', '2', 'flame_chrome', 'Chrome06', 'Chrome01', 'Shiny01'):
                jpeg = io.BytesIO()
                Image.new('RGB', (8, 8), (40, 80, 120)).save(jpeg, format='JPEG')
                (effects/(name+'.ozj')).write_bytes(bytes(24) + jpeg.getvalue())
            players = Path(tmp)/'players.txt'
            players.write_text('player Demo01 class=1 at=121,120 helm=7:9:11\n')
            out = run(root, players, '--frames', '1')
            player = out['players'][0]
            self.assertEqual(player['loaded'][1], 1)
            self.assertEqual(player['textures_missing'][1], 0)
            self.assertEqual(player['effect_textures_loaded'][1], 6)


@unittest.skipUnless(PRIVATE, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateTests(unittest.TestCase):
    def test_lorencia_demo_players(self):
        out = run(os.environ['MU_GAME_ROOT'], PLAYERS, '--frames', '120', '--placement', str(PLACEMENT),
                  '--player-range', '15', size=(320, 240), tile='128,124')
        self.assertEqual(out['summary']['item_table'], 1)
        aeris = next(p for p in out['players'] if p['name'] == 'Aeris')
        self.assertEqual(aeris['parts'][2][0], 0x1ae6 + 10)         # ArmorMale11 from Item.bmd
        self.assertTrue(all(aeris['loaded'][1:8]))                 # five parts and two weapons
        self.assertGreaterEqual(out['summary']['viewport_packets'], 6)


if __name__ == '__main__':
    unittest.main()
