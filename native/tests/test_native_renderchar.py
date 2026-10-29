"""Native world-path character rendering (NATIVE-RENDERCHAR-001).

Portable (synthetic models only): `mu-render character --world-render` draws the
reconstructed world-render passes (item level glow, excellent, back carry);
renders are deterministic, the pass counts follow the reconstructed rules,
back carry changes the weapon placement, unknown item types fall back to one
plain pass, and malformed world options are refused. `mu-render actor` with
--actor-weapon is covered by the private test (needs installed monsters).
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): an installed Dark Knight
with item levels, +15 attachments and back carry, and a monster with its
class weapon, render with every texture found.
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
import native_fixtures as nf  # noqa: E402
from test_native_character import synthetic_set  # noqa: E402

TOOL = NATIVE/'build/mu-render'
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
GAME_ROOT = os.environ.get('MU_GAME_ROOT', '')


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError(f'mu-render failed: {result.stderr}')
    return result


class WorldRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)
        cls.directory = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls.directory.name)
        player, raws = synthetic_set(11)
        cls.player = cls.tmp/'player.bmd'
        cls.player.write_bytes(player)
        cls.paths = {}
        for index, raw in raws.items():
            cls.paths[index] = cls.tmp/f'item{index}.bmd'
            cls.paths[index].write_bytes(raw)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def render(self, *extra, no_textures=True):
        args = ['character', self.player, '--world-render', '--width', '160', '--height', '120',
                '--action', '1', '--frame', '0.5']
        if no_textures:
            args += ['--no-textures']
        for slot in (1, 2, 3):
            args += ['--part', str(slot), self.paths[slot]]
        args += ['--weapon', '0', self.paths[6], '--weapon', '1', self.paths[7]]
        args += ['--item-type', 'helm=0x18e6', '--item-type', 'armor=0x1ae6', '--item-type', 'pants=0x1ce6',
                 '--item-type', 'weapon0=0xae6', '--item-type', 'weapon1=0x10e6']
        out = self.tmp/'world.png'
        result = run(*args, *extra, '--out', out)
        return json.loads(result.stdout.strip().splitlines()[-1]), out.read_bytes()

    def test_deterministic_and_levels(self):
        base, png = self.render()
        again, png2 = self.render()
        self.assertEqual(base['sha256'], again['sha256'])
        self.assertEqual(png, png2)
        self.assertEqual(base['passes'], 5)                       # one textured body per item at level 0
        high, _ = self.render('--item-level', 'all=13', '--world-time', '500')
        self.assertEqual(high['passes'], 25)                      # 2, 0x240, 0x1040, 0x48, 0x44 per item
        self.assertNotEqual(high['sha256'], base['sha256'])
        capped, _ = self.render('--item-level', 'all=13', '--quality', '1')
        self.assertEqual(capped['passes'], 10)                    # level capped at 7: body + 0x44
        exc, _ = self.render('--excellent', 'weapon0=1', '--world-time', '300')
        self.assertEqual(exc['passes'], 6)

    def test_back_carry_and_fallback(self):
        base, _ = self.render()
        carried, _ = self.render('--safe-zone')
        self.assertEqual(carried['carried'], 2)
        self.assertNotEqual(carried['sha256'], base['sha256'])
        unknown, _ = self.render('--item-type', 'weapon1=0x100')
        self.assertEqual(unknown['special'], 1)

    def test_special_wing_uses_shared_body_renderer(self):
        info, _ = self.render('--item-type', 'weapon1=0x22ea', '--item-level', 'all=13', '--world-time', '700')
        self.assertEqual((info['special'], info['passes']), (0, 21))

    def test_remaining_skin_bodies_and_sprites(self):
        early, _ = self.render('--item-type', 'helm=0x3895', '--item-level', 'helm=14', '--quality', '0')
        self.assertEqual((early['special'], early['passes']), (0, 7))
        for t in (0x389c, 0x389d):
            skin, _ = self.render('--item-type', f'helm={t}', '--world-time', '500')
            self.assertEqual((skin['special'], skin['link_sprites']), (0, 1))

    def test_native_link_saved_pose_and_capacity(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/item-render-host'], check=True, capture_output=True)
        result = subprocess.run([str(NATIVE/'build/item-render-host')], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout),
                         dict(created=13, random_calls=4, missing_bones_skipped=5, full=True))

    def test_skin_sprite_pixels_use_the_character_frame_clock(self):
        # Level-zero 0x389c has a static body and a pulsing sprite. Supply an authored texture so this
        # checks the sprite's rendered colour/scale, beyond the successful allocation count.
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow is needed for the authored JPEG texture')
        import io
        probe = self.tmp/'jpeg-probe.tga'
        probe.write_bytes(nf.tga(2, 2, 5))
        if not json.loads(run('image', probe).stdout)['jpeg']:
            self.skipTest('native renderer was built without JPEG support')
        root = self.tmp/'skin-game'
        effect = root/'Data'/'Effect'
        effect.mkdir(parents=True, exist_ok=True)
        options = ('--game-root', root, '--item-type', 'helm=0x389c')
        plain, _ = self.render(*options, '--world-time', '0', no_textures=False)
        buf = io.BytesIO()
        Image.new('RGB', (32, 32), (48, 48, 48)).save(buf, 'JPEG')
        payload = buf.getvalue()
        (effect/'Spark03.OZJ').write_bytes(payload[:24] + payload)
        start, _ = self.render(*options, '--world-time', '0', no_textures=False)
        later, _ = self.render(*options, '--world-time', '500', no_textures=False)
        self.assertEqual((start['link_sprites'], later['link_sprites']), (1, 1))
        self.assertNotEqual(start['sha256'], plain['sha256'])
        self.assertNotEqual(later['sha256'], start['sha256'])

    def test_pulse_weapon_admission_clock_and_pixels(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest('Pillow is needed for authored flare texture')
        import io
        probe = self.tmp/'pulse-jpeg-probe.tga'
        probe.write_bytes(nf.tga(2,2,5))
        if not json.loads(run('image',probe).stdout)['jpeg']:
            self.skipTest('native renderer was built without JPEG')
        root = self.tmp/'pulse-game'
        effect = root/'Data/Effect'
        effect.mkdir(parents=True,exist_ok=True)
        options = ('--game-root',root,'--item-type','weapon0=0xeee')
        plain,_ = self.render(*options,'--world-time','0',no_textures=False)
        jpeg = io.BytesIO()
        Image.new('RGB',(32,32),(48,48,48)).save(jpeg,'JPEG')
        (effect/'flare01.OZJ').write_bytes(bytes(24)+jpeg.getvalue())
        (effect/'Shiny02.OZJ').write_bytes(bytes(24)+jpeg.getvalue())
        start,_ = self.render(*options,'--world-time','0',no_textures=False)
        later,_ = self.render(*options,'--world-time','500',no_textures=False)
        self.assertEqual((start['link_sprites'],later['link_sprites']),(4,4))
        self.assertEqual(start['special'],0)
        self.assertNotEqual(start['sha256'],plain['sha256'])
        self.assertNotEqual(later['sha256'],start['sha256'])

    def test_rank5_lighting_and_named_mesh_draws(self):
        path=self.tmp/'rank5-armour.bmd'
        raw=nf.character_layout(112,bones=50,meshes=6,dummies=(9,21))
        raw=raw.replace(nf.name32('part4.tga'),nf.name32('Item1161_Blue.jpg'))
        raw=raw.replace(nf.name32('part5.tga'),nf.name32('Item1161_Black.jpg'))
        path.write_bytes(raw)
        options=('--part','2',path,'--item-type','armor=0x1c26')
        unlit,_=self.render(*options,'--lighting','0')
        lit,_=self.render(*options,'--lighting','1','--world-time','0')
        later,_=self.render(*options,'--lighting','1','--world-time','500')
        repeat,_=self.render(*options,'--lighting','1','--world-time','0')
        self.assertEqual((unlit['special'],unlit['passes']),(0,8))
        self.assertEqual((lit['special'],lit['passes']),(0,11))
        self.assertEqual(lit['sha256'],repeat['sha256'])
        self.assertNotEqual(lit['sha256'],unlit['sha256'])
        self.assertNotEqual(lit['sha256'],later['sha256'])
        path.write_bytes(raw.replace(nf.name32('Item1161_Blue.jpg'),nf.name32('other.jpg')))
        missing,_=self.render(*options,'--lighting','1','--world-time','0')
        self.assertEqual((missing['special'],missing['passes']),(0,10))

    def test_rank5_owner_effects_follow_owner_bones(self):
        """RENDER-EFFECTS-005: the lit rank-5 body reads the character's bones 35/26."""
        path=self.tmp/'rank5-owner.bmd'
        raw=nf.character_layout(114,bones=50,meshes=6,dummies=(9,21))
        raw=raw.replace(nf.name32('part4.tga'),nf.name32('Item1161_Blue.jpg'))
        raw=raw.replace(nf.name32('part5.tga'),nf.name32('Item1161_Black.jpg'))
        path.write_bytes(raw)
        options=('--part','2',path,'--item-type','armor=0x1c26','--world-time','0')
        unlit,_=self.render(*options,'--lighting','0')
        lit,_=self.render(*options,'--lighting','1')
        frames,_=self.render(*options,'--lighting','1','--frames','3','--frame-steps','2')
        self.assertEqual((unlit['owner_effects'],lit['owner_effects'],frames['owner_effects']),(0,6,18))
        short=self.tmp/'short-player.bmd'
        short.write_bytes(nf.envelope_v15(nf.character_layout(11,bones=35,actions=4,keys=(5,3,1,6),dummies=(9,21))))

        def owner(player,*extra):
            args=['character',player,'--world-render','--width','160','--height','120','--no-textures',*options,
                  '--lighting','1',*extra,'--out',self.tmp/'owner.png']
            return json.loads(run(*args).stdout.strip().splitlines()[-1])
        stopped=owner(short)
        self.assertEqual((stopped['special'],stopped['owner_effects']),(0,0))
        # +9 above the quality cap: the Blue and Black overlays follow the effects.
        ninth,bare=owner(self.player,'--item-level','armor=9'),owner(short,'--item-level','armor=9')
        self.assertEqual((ninth['owner_effects'],ninth['passes']-bare['passes']),(6,2))
        capped=owner(self.player,'--item-level','armor=9','--quality','1')
        bare=owner(short,'--item-level','armor=9','--quality','1')
        self.assertEqual((capped['owner_effects'],capped['passes']-bare['passes']),(6,0))

    def test_ranked_body_and_nine_bone_shield_use_shared_draws(self):
        path = self.tmp/'ranked-armour.bmd'
        path.write_bytes(nf.character_layout(113,bones=50,meshes=6,dummies=(9,21)))
        ordinary,_ = self.render('--part','2',path)
        body,_ = self.render('--part','2',path,'--item-type','armor=0x2024',
                             '--world-time','500')
        again,_ = self.render('--part','2',path,'--item-type','armor=0x2024',
                              '--world-time','500')
        self.assertEqual(body['special'],0)
        self.assertGreater(body['passes'],ordinary['passes'])
        self.assertEqual(body['sha256'],again['sha256'])
        shield,_ = self.render('--item-type','weapon0=0x16fa')
        self.assertEqual((shield['special'],shield['link_sprites']),(0,2))
        complete,_ = self.render('--weapon','0',path,'--item-type','weapon0=0x16fa')
        self.assertEqual((complete['special'],complete['link_sprites']),(0,9))

    def test_visible_wings_atlases_and_shield_links(self):
        wing = self.tmp/'visible-wing.bmd'
        wing.write_bytes(nf.character_layout(114,bones=20,meshes=6,dummies=(9,)))
        for t in range(0x2322,0x2328):
            low,_ = self.render('--wing',wing,'--item-type',f'wing={t}',
                                '--item-level','wing=0')
            high,_ = self.render('--wing',wing,'--item-type',f'wing={t}',
                                 '--item-level','wing=13')
            self.assertEqual((low['special'],low['passes']),(0,7))
            self.assertEqual(low['sha256'],high['sha256'])
        start,_ = self.render('--part','2',wing,'--item-type','armor=0x2002','--world-time','0')
        self.assertEqual(start['special'],0)
        self.assertGreater(start['passes'],5)
        for t in (0x16f7,0x16fb):
            full,_ = self.render('--weapon','0',wing,'--item-type',f'weapon0={t}')
            missing,_ = self.render('--item-type',f'weapon0={t}')
            self.assertEqual((full['link_sprites'],missing['link_sprites']),(10,2 if t==0x16f7 else 0))

    def test_seed_single_mesh_remains_visible(self):
        path = self.tmp/'seed-one-mesh.bmd'
        path.write_bytes(nf.character_layout(116,bones=3,meshes=1))
        plain,_ = self.render('--weapon','0',path)
        seed,_ = self.render('--weapon','0',path,'--item-type','weapon0=0x2322')
        other,_ = self.render('--weapon','0',path,'--item-type','weapon0=0x2327')
        self.assertEqual(seed['special'],0)
        self.assertGreater(seed['triangles'],plain['triangles'])
        self.assertNotEqual(seed['sha256'],other['sha256'])

    def test_refuses_malformed_options(self):
        for bad in (('--item-level', 'nine'), ('--item-level', 'sleeve=3'), ('--glow-color', '1,2'),
                    ('--actor-weapon', 'x')):
            result = run('character', self.player, *bad, '--out', self.tmp/'x.png', check=False)
            self.assertNotEqual(result.returncode, 0, bad)

    @unittest.skipUnless(PRIVATE and GAME_ROOT, 'installed client renders are opt-in')
    def test_private_installed_world_renders(self):
        # monster class 0 carries item 0x0cec (group 1, index 6: Axe07) in weapon slot 0
        root = Path(GAME_ROOT)
        result = run('character', '--game-root', root, '--class', '1', '--weapon', '0', root/'Data/Item/Sword01.bmd',
                     '--weapon', '1', root/'Data/Item/Shield01.bmd', '--world-render', '--item-level', 'all=15',
                     '--attachments', '--world-time', '900', '--out', self.tmp/'dk.png')
        info = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(info['attachments'], 9)
        self.assertEqual(info['special'], 0)
        result = run('character', '--game-root', root, '--class', '1', '--weapon', '0', root/'Data/Item/Sword01.bmd',
                     '--world-render', '--safe-zone', '--out', self.tmp/'carry.png')
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1])['carried'], 1)
        result = run('actor', '--game-root', root, '--type', '0', '--world-render', '--actor-weapon',
                     f"0={root/'Data/Item/Axe07.bmd'}", '--out', self.tmp/'monster.png')
        info = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual((info['weapons'], info['listed']), (1, 1))


if __name__ == '__main__':
    unittest.main()
