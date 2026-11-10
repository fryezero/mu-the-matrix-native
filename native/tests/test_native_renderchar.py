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

    def test_skeleton_body_level_passes(self):
        for model in (0x422, 0x423, 0x424):
            low, _ = self.render('--item-type', f'helm={model}', '--world-time', '0')
            high, png = self.render('--item-type', f'helm={model}', '--item-level', 'helm=8',
                                    '--world-time', '0')
            self.assertEqual((low['special'], low['passes']), (0, 5))
            self.assertEqual((high['special'], high['passes']), (0, 6))
            self.assertNotEqual(high['sha256'], low['sha256'])
            again, repeat = self.render('--item-type', f'helm={model}', '--item-level', 'helm=8',
                                         '--world-time', '0')
            self.assertEqual((high['sha256'], png), (again['sha256'], repeat))

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

    def test_named_part_mesh_inputs_and_missing_names(self):
        path = self.tmp/'named-parts.bmd'
        raw = nf.character_layout(118, bones=50, meshes=6, dummies=(9, 21))
        labelled = raw.replace(nf.name32('part1.tga'), nf.name32('Item1161_Blue.jpg'))
        labelled = labelled.replace(nf.name32('part2.tga'), nf.name32('Item1161_Black.jpg'))
        labelled = labelled.replace(nf.name32('part3.tga'), nf.name32('Item1161_skirt.jpg'))
        labelled = labelled.replace(nf.name32('part4.tga'), nf.name32('Item1161_Blue.jpg'))
        for item, overlays in ((0x1a26, 2), (0x1e26, 2), (0x2026, 1), (0x2226, 1)):
            options = ('--part', '2', path, '--item-type', f'armor={item}', '--world-time', '0')
            path.write_bytes(raw)
            missing, _ = self.render(*options)
            path.write_bytes(labelled)
            present, _ = self.render(*options)
            self.assertEqual((missing['special'], present['special']), (0, 0))
            self.assertEqual(present['passes'], missing['passes'] + overlays)
            self.assertGreater(present['triangles'], missing['triangles'])
            path.write_bytes(labelled.replace(nf.name32('Item1161_Blue.jpg'),
                                              nf.name32('other-blue.jpg'), 1))
            later_match, _ = self.render(*options)
            self.assertEqual(later_match['passes'], present['passes'])

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

    def test_armour_owner_effect_program(self):
        """RENDER-ITEMS-002Q: the worn chest piece 0x1bc3 runs its owner-effect program (eight 0x7f7a sprites at
        owner bones 26/27/36/18, 0x8109 at bone 35, then rand() % 2 gates particle 0x810a/7). Requests no native
        kind creates count as owner_refused; a 35-bone part model is outside the program's bone domain.
        RENDER-EFFECTS-017: 0x810a/7 is a native kind, so its request is created, not refused."""
        path=self.tmp/'owner-fx.bmd'
        path.write_bytes(nf.character_layout(114,bones=50,meshes=6,dummies=(9,21)))
        options=('--part','2',path,'--item-type','armor=0x1bc3','--world-time','0')
        one,_=self.render(*options)
        frames,_=self.render(*options,'--frames','3','--frame-steps','2')
        self.assertEqual((one['special'],one['owner_effects'],one['owner_refused']),(0,9,0))
        # Over three frames one rand() % 2 gate opens: its CreateParticle 0x810a/7 is created (RENDER-EFFECTS-017).
        self.assertEqual((frames['owner_effects'],frames['owner_refused']),(28,0))
        short=self.tmp/'owner-fx-short.bmd'
        short.write_bytes(nf.character_layout(114,bones=35,meshes=6,dummies=(9,21)))
        outside,_=self.render('--part','2',short,'--item-type','armor=0x1bc3','--world-time','0')
        self.assertEqual((outside['special'],outside['owner_effects'],outside['owner_refused']),(0,0,1))

    def test_weapon_pre_draw_program(self):
        """RENDER-ITEMS-002R: RenderObjDraw's own case of sword 0x0b27 creates bone sprites on the weapon's own
        posed bones (constant indices) before the body draws; bow 0x1311 looks its bone up by name ("a02"), which
        the synthetic skeleton (cbone0..) lacks. EFFECTS-025 supplies the explicit pre-bone record for that sprite."""
        path=self.tmp/'pre-fx.bmd'
        path.write_bytes(nf.character_layout(115,bones=12,meshes=2))
        sword,_=self.render('--weapon','0',path,'--item-type','weapon0=0xb27','--world-time','0')
        again,_=self.render('--weapon','0',path,'--item-type','weapon0=0xb27','--world-time','0')
        self.assertEqual((sword['special'],sword['pre_refused']),(0,0))
        self.assertGreater(sword['pre_effects'],0)
        self.assertEqual(sword['sha256'],again['sha256'])
        bow,_=self.render('--weapon','0',path,'--item-type','weapon0=0x1311','--world-time','0')
        self.assertEqual((bow['special'],bow['pre_effects'],bow['pre_refused']),(0,1,0))

    def test_read_program_and_no_glow_bodies(self):
        """002X bodies reach native drawing with deterministic fixed-pose fixture models."""
        path = self.tmp/'items-002x.bmd'
        path.write_bytes(nf.character_layout(115, bones=64, meshes=6))
        for t in (0x0b29, 0x0b52, 0x0f1e, 0x174a, 0x2301, 0x2302, 0x23a8, 0x23a9,
                  0x23ed, 0x23ee, 0x23fe, 0x23ff, 0x2403, 0x2404,
                  0x232c, 0x232d, 0x232e, 0x232f, 0x2330, 0x26f5):
            options = ('--weapon', '0', path, '--item-type', f'weapon0={t:#x}',
                       '--item-level', 'weapon0=9', '--world-time', '123456',
                       '--frame-counter', '2147483648', '--item-body-only')
            first, _ = self.render(*options)
            second, _ = self.render(*options)
            self.assertEqual(first['special'], 0, hex(t))
            self.assertEqual(first['sha256'], second['sha256'], hex(t))
            self.assertGreater(first['passes'], 0, hex(t))

    def test_wing_joint_and_random_bone_programs(self):
        """RENDER-ITEMS-002S: wing 0x22ec's case creates twenty CreateJoint requests (0x7f7c/0xe, 0x7fd3/4) along
        its own bones; RENDER-ITEMS-002U: the joint pool reconstructs both kinds, so all twenty are created and drawn
        in the same frame (ten-tail streaks: up to 9 segments x 2 faces each), as are 0x248f's. Wing 0x23ef places
        sprites at bones rand() % bone count (always inside the skeleton) and at constant bones up to 50: on 64
        bones nothing is refused, on 40 the two requests at bones 44 and 50 are."""
        path=self.tmp/'pre-fx-wing.bmd'
        path.write_bytes(nf.character_layout(114,bones=64,meshes=2))
        for wing in ('0x22ec','0x248f'):
            joint,_=self.render('--wing',path,'--item-type','wing='+wing,'--world-time','0')
            self.assertEqual((joint['special'],joint['pre_refused']),(0,0))
            self.assertGreater(joint['pre_effects'],20)
            self.assertEqual(joint['joint_quads'],20*18)
        spread,_=self.render('--wing',path,'--item-type','wing=0x23ef','--world-time','0')
        self.assertEqual((spread['special'],spread['pre_refused']),(0,0))
        self.assertGreater(spread['pre_effects'],0)
        short=self.tmp/'pre-fx-wing-40.bmd'
        short.write_bytes(nf.character_layout(114,bones=40,meshes=2))
        cut,_=self.render('--wing',short,'--item-type','wing=0x23ef','--world-time','0')
        self.assertEqual((cut['special'],cut['pre_refused'],cut['pre_effects']),(0,2,spread['pre_effects']-2))

    def test_post_program_and_frame_counter_gate(self):
        """RENDER-ITEMS-002T: 0x2713's block after its RenderPartObjectBody draws places three sprites at its own bones
        8, 10 and 11: on 12 bones all are created, on 10 the last two are refused. Mace 0x0f20's particles follow
        tests of the rendered-frame counter, which the native env does not supply by default, so they are refused
        and counted. EFFECTS-025 supplies the separate pre-bone record for its missing-name sprites."""
        path=self.tmp/'post-fx.bmd'
        path.write_bytes(nf.character_layout(115,bones=12,meshes=2))
        post,_=self.render('--weapon','0',path,'--item-type','weapon0=0x2713','--world-time','0')
        self.assertEqual((post['special'],post['pre_effects'],post['pre_refused']),(0,3,0))
        short=self.tmp/'post-fx-10.bmd'
        short.write_bytes(nf.character_layout(115,bones=10,meshes=2))
        cut,_=self.render('--weapon','0',short,'--item-type','weapon0=0x2713','--world-time','0')
        self.assertEqual((cut['special'],cut['pre_effects'],cut['pre_refused']),(0,1,2))
        mace,_=self.render('--weapon','0',path,'--item-type','weapon0=0xf20','--world-time','0')
        self.assertEqual((mace['special'],mace['pre_effects']),(0,17))
        self.assertGreater(mace['pre_refused'],0)

    def test_frame_counter_option(self):
        """RENDER-ITEMS-002U: with the rendered-frame counter supplied (mu-render --frame-counter, as the world
        runtime's own counter), mace 0x0f20's requests behind its counter tests run only on the frames the client
        runs them: two particles 0x855d/1 when counter % 3 == 0, one 0x84d1/1 when counter % 5 == 0. Without a
        counter the three gated particle requests are refused. EFFECTS-025 admits the 17 missing-name sprites
        through the explicit native pre-bone record. Particle positions still require the absent named bones."""
        path=self.tmp/'counter-fx.bmd'
        path.write_bytes(nf.character_layout(115,bones=12,meshes=2))
        base,_=self.render('--weapon','0',path,'--item-type','weapon0=0xf20','--world-time','0')
        self.assertEqual((base['pre_effects'],base['pre_refused']),(17,3))
        for frame in (0,1,2,3,5,6,10,15,0xffffffff):
            r,_=self.render('--weapon','0',path,'--item-type','weapon0=0xf20','--world-time','0',
                            '--frame-counter',str(frame))
            expect=2*(frame%3==0)+(frame%5==0)
            self.assertEqual((r['special'],r['pre_effects'],r['pre_refused']),(0,17,expect),frame)

        isolated, _ = self.render('--weapon', '0', path, '--item-type', 'weapon0=0xf20',
                                  '--world-time', '0', '--frame-counter', '0', '--item-body-only')
        self.assertEqual((isolated['special'], isolated['pre_effects'], isolated['pre_refused']), (0, 0, 0))
        self.assertEqual(isolated['particles_created'], 0)
        self.assertGreater(isolated['passes'], 0)

    def test_counter_range_bodies_reach_native_renderer(self):
        """The six 002V types used to fall back as unsupported. Exercise their recipes through the
        native item host, including a high-bit frame counter and the staff's intermediate colour products."""
        path = self.tmp/'counter-range.bmd'
        path.write_bytes(nf.character_layout(115, bones=16, meshes=8))
        for t in (0xf24, 0xf28, 0xf29, 0xf2b, 0xf2c, 0x1588):
            args = ('--weapon', '0', path, '--item-type', f'weapon0={t:#x}', '--world-time', '123456',
                    '--frame-counter', '4294967295')
            result, png = self.render(*args)
            again, repeat = self.render(*args)
            self.assertEqual(result['special'], 0, hex(t))
            self.assertGreater(result['passes'], 5, hex(t))
            self.assertEqual((result['sha256'], png), (again['sha256'], repeat), hex(t))

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
    def test_private_worn_mace_counter_atlas(self):
        """The worn caller resets OBJECT+a8 to one before 0x0f2a draws its counter atlas."""
        import random
        import struct
        sys.path.insert(0, str(NATIVE.parent/'scripts'))
        import pins
        import validate_items as vi
        import actor_machine as am
        machine = vi.Machine(pins.TEXT.read(), pins.DATA.read())
        for clock in (0.0, 1.0, 123456.0, -8000.0):
            host = vi.HostCase(random.Random(0xf2a), world_time=clock)
            obj = am.undefined_region('object', vi.OBJ, 0x400, 0x47)
            obj.define(vi.OBJ+0x5c, struct.pack('<i', 0xf2a))
            poison = bytes(am.poison(0x400, 0x47))
            for offset in (0x68, 0x74):
                obj.define(vi.OBJ+offset, poison[offset:offset+4])
            stubs = host.stubs()
            stubs[0x01295f18] = lambda m: 0
            result = machine.execute_regions(vi.OBJECT_ATTR, [vi.OBJ],
                [obj, am.defined_region('time', vi.TIME, struct.pack('<f', clock), writable=False)], stubs)
            self.assertIsNone(result['error'])
            self.assertIsNone(result['stopped'])
            data = result['regions']['object']
            self.assertEqual(struct.unpack_from('<I', data, 0xa8)[0], 0x3f800000)
            self.assertEqual(struct.unpack_from('<i', data, 0x74)[0], -1)
        hashes = []
        root = Path(GAME_ROOT)
        for counter in (0, 7, 8):
            output = self.tmp/f'counter-atlas-{counter}.png'
            result = run('character', '--game-root', root, '--class', '1',
                         '--weapon', '0', root/'Data/Item/Hammer15.bmd', '--world-render', '--item-body-only',
                         '--item-type', 'weapon0=0x0f2a', '--item-level', 'weapon0=9',
                         '--action', '1', '--frame', '0.5', '--world-time', '123456',
                         '--frame-counter', str(counter), '--width', '640', '--height', '480',
                         '--out', output)
            report = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertEqual(report['special'], 0)
            self.assertEqual((report['pre_effects'], report['pre_refused'], report['particles_created']), (0, 0, 0))
            hashes.append(report['sha256'])
        self.assertEqual(len(set(hashes)), 3, 'fixed-pose atlas must visibly follow the counter')

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
