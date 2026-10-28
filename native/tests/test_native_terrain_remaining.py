"""Synthetic integration regressions for RENDER-TERRAIN-002, no client inputs."""
import ctypes as C
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from test_native_terrain import Build, LIBRARY, ozj_tga, run, v12_encrypt, write_world
import native_fixtures as nf
import validate_terrain as v
import validate_terrain_remaining as remaining


class RemainingTerrainTests(Build):
    def test_signed_layout_and_negative_stencil(self):
        g=remaining.Grid()
        self.assertEqual((remaining.Grid.active.offset,remaining.Grid.count.offset,C.sizeof(g)),
                         (0x100004,0x114ad4,0x114ad8))
        lib=C.CDLL(str(LIBRARY))
        lib.mu_terrain_signed_init.argtypes=[C.c_void_p,C.c_int32]
        lib.mu_terrain_signed_step.argtypes=[C.c_void_p]
        lib.mu_terrain_signed_init(C.byref(g),0x18)
        i=64*256+64
        for offset in (-256,256,-1,1):g.grid[v.CELLS+i+offset]=-17
        lib.mu_terrain_signed_step(C.byref(g))
        # (-68 >> 1) - (-34 >> 4), arithmetic right shift.
        self.assertEqual(g.grid[i],-31)
        self.assertEqual(g.grid[0],0)

    def test_signed_height_and_invalid_coordinates(self):
        g=remaining.Grid(); lib=C.CDLL(str(LIBRARY))
        lib.mu_terrain_signed_height.argtypes=[C.c_void_p,C.c_float,C.c_float]
        lib.mu_terrain_signed_height.restype=C.c_float
        g.active=1;i=20*256+10
        for n,value in enumerate([999999,-400,-100,100]):g.grid[n*v.CELLS+i]=value
        self.assertEqual(lib.mu_terrain_signed_height(C.byref(g),500,1000),75)
        self.assertEqual(lib.mu_terrain_signed_height(C.byref(g),-100,1000),0)
        self.assertEqual(lib.mu_terrain_signed_height(C.byref(g),12800,1000),0)

    def test_overlay_worlds_render_with_both_layers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for world in (0x71,0x91):
                folder=world+1;data=write_world(root,folder,seed=9,rgb=world==0x91)
                plain=bytes([0,folder,255,255])+struct.pack('<H',0x2000)*v.CELLS
                encoded=bytes(b^v.KEY[i%3] for i,b in enumerate(plain))
                (data/f'EncTerrain{folder}.att').write_bytes(v12_encrypt(encoded))
                texture=root/'Data/World114/cubemap_up.OZJ';texture.parent.mkdir(parents=True,exist_ok=True)
                texture.write_bytes(ozj_tga(32,32,22))
                args=['--world',world,'--width',120,'--height',80,'--target','12800,12800','--distance',2500]
                low=json.loads(run('render',root,*args,'--detail',3).stdout)
                high=json.loads(run('render',root,*args,'--detail',4).stdout)
                self.assertEqual((high['status'],high['unsupported'],high['missing_texture_binds']),(0,0,0))
                self.assertNotEqual(low['sha256'],high['sha256'])

    def test_kalima_native_draw_is_dynamic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);write_world(root,25,seed=10)
            assets=root/'Data/Object25';assets.mkdir(parents=True)
            # OZTs wrap the first four TGA bytes in front of the payload.
            tga=nf.tga(32,32,1,alpha=True);(assets/'water1.OZT').write_bytes(tga[:4]+tga)
            (assets/'water2.OZJ').write_bytes(ozj_tga(32,32,9))
            args=['--world',0x18,'--width',160,'--height',100,'--target','6400,6400','--distance',2000]
            a=json.loads(run('render',root,*args,'--time',1000).stdout)
            b=json.loads(run('render',root,*args,'--time',2000).stdout)
            self.assertEqual((a['status'],a['faces'],a['missing_texture_binds']),(0,3362,0))
            self.assertNotEqual(a['sha256'],b['sha256'])

    def test_chaos_smoke_reaches_native_particle_pool(self):
        from test_native_world import write_open_world
        with tempfile.TemporaryDirectory() as tmp:
            root=write_open_world(Path(tmp)/'game');write_world(root,19,seed=3)
            effect=root/'Data/Effect';effect.mkdir()
            tga=nf.tga(32,32,7,alpha=True);(effect/'smoke05.ozt').write_bytes(tga[:4]+tga)
            tool=Path(__file__).resolve().parents[1]/'build/mu-walk'
            r=subprocess.run([str(tool),'--game-root',str(root),'--world','18','--tile','24,77',
                '--headless','--frames','20','--every','20','--width','120','--height','80',
                '--backend','soft','--no-audio','--no-env','--no-items','--no-names','--no-map','--quiet',
                '--out-dir',str(Path(tmp)/'out')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            rows=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
            particles=next(row for row in rows if row.get('particles') is True)
            self.assertGreater(particles['created'],0)
            self.assertGreater(particles['drawn_particles'],0)
            self.assertEqual((particles['unsupported'],particles['overflow']),(0,0))

    def test_unaffected_water_world_keeps_optional_emitter_disabled(self):
        from test_native_world import write_open_world
        with tempfile.TemporaryDirectory() as tmp:
            root=write_open_world(Path(tmp)/'game');write_world(root,35,seed=3)
            tool=Path(__file__).resolve().parents[1]/'build/mu-walk'
            r=subprocess.run([str(tool),'--game-root',str(root),'--world','34','--tile','128,128',
                '--headless','--frames','10','--every','10','--width','120','--height','80',
                '--backend','soft','--no-audio','--no-env','--no-items','--no-names','--no-map','--quiet',
                '--out-dir',str(Path(tmp)/'out')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            rows=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
            particles=next(row for row in rows if row.get('particles') is True)
            self.assertEqual((particles['created'],particles['unsupported']),(0,0))

    def test_camera_worlds_accept_frustum(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for world in (6,0x49):
                write_world(root,world+1)
                r=json.loads(run('render',root,'--world',world,'--width',80,'--height',60,
                                 '--frustum','12800,12800').stdout)
                self.assertEqual(r['frustum_status'],0)


if __name__=='__main__':unittest.main()
