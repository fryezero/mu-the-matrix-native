"""Portable bow trail and native draw regressions; pinned comparison is a separate registry row."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'native/tests'))
import validate_joints as jt
import native_fixtures as nf
F3 = C.c_float * 3


class Trails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/joints')], check=True)
        cls.lib = jt.load_library(ROOT/f'reconstructed/joints/libclient_joints.{jt.SUFFIX}')

    def create(self, kind, key=80, colour=None):
        j, env = jt.Joint(), jt.Env()
        if colour:
            env.has_creation_light = 1
            env.creation_light[:] = colour
        self.assertEqual(self.lib.mu_jt_create(C.byref(j), kind[0], F3(1,2,3), F3(4,5,6), F3(), kind[1], -1,
                                              40, key, 0, 0, 0xffff, 0, C.byref(env)), 1)
        return j

    def test_flare_key_signed_lifetime_and_colours(self):
        for sub, tails in ((12,16),(18,7),(22,9)):
            j = self.create((0x7f79,sub))
            self.assertEqual((j.lifetime,j.key,j.max_tails),(80,0,tails))
        self.assertEqual(self.create((0x7f79,12),0xffff).lifetime,-1)
        self.assertEqual(list(self.create((0x7f79,18)).light),[0.5]*3)
        self.assertEqual(list(self.create((0x7f79,18),colour=(0.25,0.5,1)).light),[0.25,0.5,1])

    def test_width_faces_uv_and_initial_tail(self):
        for kind,tails in (((0x814c,10),8),((0x8182,10),10),((0x8185,10),10)):
            j = self.create(kind,colour=(0.25,0.5,1))
            self.assertEqual((j.faces,j.max_tails,j.lifetime,j.velocity),(2,tails,30,60))
            self.assertEqual(list(j.light),[0.25,0.5,1])
        self.assertEqual(self.create((0x85cc,0)).field_a25,5)
        j = self.create((0x828c,2))
        self.assertEqual((j.num_tails,j.max_tails,j.field_a25),(-1,6,2))

    def test_null_owner_death_keeps_distinct_tail_rules(self):
        a,b,c = [self.create(k) for k in ((0x80e3,4),(0x80e4,1),(0x85cc,0))]
        inputs = jt.MoveInputs(0.1,0,0,0,0)
        for j in (a,b,c): self.lib.mu_jt_move(C.byref(j),None,C.byref(inputs))
        self.assertEqual((a.live,a.lifetime,a.num_tails),(0,-1,1))
        self.assertEqual((b.live,b.lifetime,b.num_tails),(0,20,0))
        self.assertEqual((c.live,c.lifetime,c.num_tails),(0,19,1))


class Native(unittest.TestCase):
    def test_arrow_arguments_and_model_draws(self):
        native = ROOT/'native'
        subprocess.run(['make','-s','-C',str(native),'build/libmunative.a','build/libmusession_world.a'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            host=tmp/'host'
            obj=tmp/'host.o'
            command=['clang','-std=c11','-O2','-ffp-contract=off','-I',str(native/'build/gen'),
                     '-I',str(native/'session'),'-c',str(native/'tests/effects12_host.c'),'-o',str(obj)]
            p=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            command=['clang++',str(obj),str(native/'build/libmunative.a'),str(native/'build/libmusession_world.a'),'-lm','-o',str(host)]
            if sys.platform=='darwin':
                command += ['-L/opt/homebrew/opt/cryptopp/lib','-lcryptopp',
                            '-L/opt/homebrew/opt/jpeg-turbo/lib','-ljpeg',
                            '-framework','CoreText','-framework','CoreGraphics','-framework','CoreFoundation']
            else: command += ['-lcryptopp','-ljpeg']
            p=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            for directory,filename in [('Skill','absolute_gunbow_arrow.bmd'),('Effect','multishot02.bmd')]:
                d=tmp/'Data'/directory; d.mkdir(parents=True,exist_ok=True)
                (d/filename).write_bytes(nf.synthetic_layout(413,actions=1,keys=(8,)))
            p=subprocess.run([str(host),str(tmp)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn('gunbow white double draw: OK',p.stdout)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions_and_compiled_mutants(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_effects12.py'),
                            '--cases','2','--mutations','--output',str(out)],check=True,capture_output=True)
            report=json.loads(out.read_text())
        self.assertTrue(report['all_equal'])
        self.assertTrue(report['all_mutants_caught'])
        self.assertEqual(report['instruction_cases'],64)
        self.assertEqual(len(report['mutants']),22)


if __name__=='__main__': unittest.main()
