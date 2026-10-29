"""BUILD-DEPS-001: header changes rebuild exactly the objects that include them.

Every compile writes a .d file (-MMD -MP, or one -MM pass for a call that compiles several sources)
that the Makefiles include. `make -q -W <header>` asks make whether a target would be rebuilt if
<header> had just changed, without touching any file.
"""
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
RECON = NATIVE.parent / 'reconstructed'


def make(directory, *args):
    return subprocess.run(['make', '-C', str(directory), *args], capture_output=True, text=True)


@unittest.skipUnless(shutil.which('make') and shutil.which('clang'), 'make and clang are required')
class BuildDepsTests(unittest.TestCase):
    def assert_stale(self, directory, header, target, stale, *args):
        result = make(directory, '-q', '-W', header, *args, target)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        self.assertEqual(result.returncode == 1, stale, f'{target} after a change to {header}')

    def test_native_objects_and_one_call_tools(self):
        with tempfile.TemporaryDirectory() as folder:
            build = Path(folder) / 'build'
            wav, hero, proto = build / 'audio/mu_wav.o', build / 'audio/recon_hero_sound.o', build / 'mu-proto'
            built = make(NATIVE, f'BUILD={build}', str(wav), str(hero), str(proto))
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertTrue(wav.with_suffix('.d').is_file())
            for target in (wav, hero, proto):
                self.assertEqual(make(NATIVE, '-q', f'BUILD={build}', str(target)).returncode, 0, target)
            # The audio objects once shared one hand-written header list; now only the includer goes stale.
            self.assert_stale(NATIVE, 'core/mu_wav.h', str(wav), True, f'BUILD={build}')
            self.assert_stale(NATIVE, 'core/mu_wav.h', str(hero), False, f'BUILD={build}')
            self.assert_stale(NATIVE, '../reconstructed/audio/hero_sound.h', str(hero), True, f'BUILD={build}')
            self.assert_stale(NATIVE, '../reconstructed/audio/hero_sound.h', str(wav), False, f'BUILD={build}')
            # mu-proto compiles two sources in one call: the first source's header path comes from the -MM pass.
            self.assert_stale(NATIVE, 'tools/../core/mu_protocol.h', str(proto), True, f'BUILD={build}')
            self.assert_stale(NATIVE, 'tools/../core/mu_protocol.h', str(wav), False, f'BUILD={build}')

    def test_reconstructed_libraries(self):
        mix, codec = RECON / 'mix', RECON / 'model-codec'
        suffix = 'dylib' if platform.system() == 'Darwin' else 'so'
        for directory, targets in ((mix, [f'libmix.{suffix}']),
                                   (codec, [f'libmodelcodec.{suffix}', f'libbonetracks.{suffix}'])):
            built = make(directory, *targets)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertEqual(make(directory, '-q', *targets).returncode, 0, directory)
        # item_services.h is in no hand-written list of reconstructed/mix/Makefile.
        self.assert_stale(mix, 'item_services.h', f'libmix.{suffix}', True)
        self.assert_stale(codec, 'bone_tracks.h', f'libbonetracks.{suffix}', True)
        self.assert_stale(codec, 'bone_tracks.h', f'libmodelcodec.{suffix}', False)


if __name__ == '__main__':
    unittest.main()
