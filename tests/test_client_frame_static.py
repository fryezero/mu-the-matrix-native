"""Synthetic checks for scripts/client_frame_static.py (CLIENT-FRAME-001).

No game bytes are used: code fixtures are short hand-assembled sequences at
made-up addresses and the PE fixtures are minimal authored export tables. The
private pinned-input check runs only with MU_RECOVERY_INTEGRATION=1.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


frame = load('client_frame_static', ROOT/'scripts/client_frame_static.py')
common = load('model_hierarchy_common', ROOT/'scripts/model_hierarchy_common.py')
minimal_pe = load('render_static_fixtures', ROOT/'tests/test_client_render_static.py').minimal_pe

BASE = 0x00401000


def text_of(code):
    return frame.render.Text(common.Region(BASE, bytes(code)+b'\xcc'*64))


def ff15(slot):
    return b'\xff\x15'+struct.pack('<I', slot)


class ImportNamingTests(unittest.TestCase):
    def test_blocks_split_on_zero_and_name_against_each_dll(self):
        winmm = minimal_pe(0x6f240000, {'timeGetTime': 0x152c0, 'timeBeginPeriod': 0x15300})
        gdi = minimal_pe(0x6da80000, {'SwapBuffers': 0x2a090})
        dlls = {'winmm.dll': frame.render.pe_exports(winmm), 'gdi32.dll': frame.render.pe_exports(gdi)}
        values = [0x6f2552c0, 0x6f255300, 0, 0x6daaa090, 0x12345678, 0]
        data = common.Region(0x01a7c000, struct.pack(f'<{len(values)}I', *values))
        self.assertEqual(len(frame.import_blocks(data, 0x01a7c000, 0x01a7c018)), 2)
        slots, blocks = frame.name_imports(data, dlls, 0x01a7c000, 0x01a7c018)
        self.assertEqual(slots[0x01a7c000], ('winmm.dll', 'timeGetTime'))
        self.assertEqual(slots[0x01a7c004], ('winmm.dll', 'timeBeginPeriod'))
        self.assertEqual(slots[0x01a7c00c], ('gdi32.dll', 'SwapBuffers'))
        self.assertNotIn(0x01a7c010, slots)
        self.assertEqual([(b['slots'], b['named']) for b in blocks], [(2, 2), (2, 1)])

    def test_unpinned_dll_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            payload = minimal_pe(0x10000000, {'Sleep': 0x1000})
            (Path(folder)/'kernel32.dll').write_bytes(payload)
            with self.assertRaises(ValueError):
                frame.load_dlls(folder, {'kernel32.dll': '0'*64})
            pins = {'kernel32.dll': hashlib.sha256(payload).hexdigest()}
            self.assertIn('kernel32.dll', frame.load_dlls(folder, pins))

    def test_slot_references_find_calls_thunks_and_loads(self):
        slot = 0x01a7c4a0
        packed = struct.pack('<I', slot)
        code = ff15(slot)+b'\x90'+b'\xff\x25'+packed+b'\xa1'+packed+b'\x8b\x3d'+packed
        refs = frame.slot_references(text_of(code), slot)
        self.assertEqual(refs, {'calls': [BASE], 'jumps': [BASE+7], 'loads': [BASE+13, BASE+18]})


class FrameCapReadingTests(unittest.TestCase):
    def cap_code(self, limit):
        # elapsed = [ebp-0x10]; if elapsed < limit: Sleep(limit - elapsed); elapsed = limit
        code = bytearray(b'\x55\x8b\xec')
        code += b'\x83\x7d\xf0'+bytes([limit])                  # cmp dword [ebp-0x10], limit
        code += b'\x7d\x14'                                      # jge past the store
        code += b'\x6a'+bytes([limit])+b'\x58\x2b\x45\xf0\x50'   # push limit; pop eax; sub eax,[ebp-0x10]; push eax
        code += ff15(0x01a7c4a0)                                 # call [Sleep]
        code += b'\xc7\x45\xf0'+struct.pack('<I', limit)         # mov dword [ebp-0x10], limit
        code += b'\xc9\xc3'
        return code

    def test_cap_immediates_and_exact_texts(self):
        code = self.cap_code(0x21)
        text = text_of(code)
        fields = frame.cap_fields(text, [(BASE+3, BASE+6, '837df021'), (BASE+9, BASE+10, '6a21'),
                                         (BASE+22, BASE+25, 'c745f021000000')])
        self.assertEqual([f['immediate'] for f in fields], [0x21]*3)
        self.assertTrue(all(f['match'] for f in fields))
        checks = frame.check_instructions(text, [(BASE+3, 'cmp dword ptr [ebp - 0x10], 0x21'),
                                                 (BASE+7, 'jge 0x40101d'), (BASE+16, 'call dword ptr [0x1a7c4a0]'),
                                                 (BASE+22, 'mov dword ptr [ebp - 0x10], 0x28')])
        self.assertEqual([c['match'] for c in checks], [True, True, True, False])
        self.assertEqual(checks[3]['actual'], 'mov dword ptr [ebp - 0x10], 0x21')
        # A different encoding of the same limit is reported as a byte mismatch.
        other = frame.cap_fields(text_of(self.cap_code(0x10)), [(BASE+3, BASE+6, '837df021')])
        self.assertEqual((other[0]['immediate'], other[0]['match']), (0x10, False))


class DrawSiteTests(unittest.TestCase):
    SLOTS = {0x01a7c750: 'glBegin', 0x01a7c760: 'glEnd', 0x01a7c774: 'glTexCoord2f', 0x01a7c684: 'glVertex2f',
             0x01a7c778: 'glVertex3fv', 0x01a7c75c: 'glEnable'}

    def test_fan_site_mode_return_address_and_vertex_calls(self):
        code = bytearray(b'\x55\x8b\xec')
        code += b'\x6a\x06'                                  # push GL_TRIANGLE_FAN
        site = BASE+len(code)
        code += ff15(0x01a7c750)
        for _ in range(4):
            code += ff15(0x01a7c774)+ff15(0x01a7c684)
        code += ff15(0x01a7c760)+ff15(0x01a7c75c)+b'\xc9\xc3'
        caller = BASE+len(code)
        code += b'\xe8'+struct.pack('<i', BASE-(caller+5))+b'\xc3'
        records = frame.glbegin_sites(text_of(code), self.SLOTS, {BASE: ('2d', 'test rectangle')})
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual((record['site'], record['return_address'], record['function'], record['mode']),
                         (hex(site), hex(site+6), hex(BASE), 'GL_TRIANGLE_FAN'))
        self.assertEqual(record['vertex_calls'], {'glTexCoord2f': 4, 'glVertex2f': 4})
        self.assertTrue(record['two_d'])
        self.assertEqual((record['raw_callers'], record['category']), (1, '2d'))

    def test_non_immediate_mode_and_line_sites_are_not_hot(self):
        code = bytearray(b'\x55\x8b\xec\x6a\x01')+ff15(0x01a7c750)+ff15(0x01a7c760)   # GL_LINES
        code += b'\xff\x75\x08'+ff15(0x01a7c750)+ff15(0x01a7c760)+b'\xc9\xc3'         # push [ebp+8]
        records = frame.glbegin_sites(text_of(code), self.SLOTS, {})
        self.assertEqual([r['mode'] for r in records], ['GL_LINES', None])
        self.assertNotIn('vertex_calls', records[0])


class BufferObjectTests(unittest.TestCase):
    def test_pointer_slot_call_arguments(self):
        slot = 0x01a7cb80
        code = bytearray(b'\x55\x8b\xec')
        code += b'\x8d\x45\xa0\x50'                          # lea eax,[ebp-0x60]; push eax (data)
        code += b'\x68\x90\x00\x00\x00\x6a\x00'              # push 0x90; push 0
        code += b'\x68\x92\x88\x00\x00'                      # push GL_ARRAY_BUFFER
        load = BASE+len(code)
        code += b'\xa1'+struct.pack('<I', slot)              # mov eax,[slot]
        call = BASE+len(code)
        code += b'\xff\x10\xc9\xc3'                          # call [eax]
        text = text_of(code)
        self.assertEqual(frame.pointer_calls(text, slot), [(load, call)])
        self.assertEqual(frame.pushes_before(text, call)[:4], ['0x8892', '0', '0x90', 'eax'])

    def test_creation_parameters(self):
        code = bytearray(b'\x55\x8b\xec\x83\xec\x14')
        code += b'\xc7\x45\xec\x0b\x00\x00\x00'              # flags 0xb
        code += b'\xc7\x45\xf4\x40\x01\x00\x00'              # size 0x140
        code += b'\xc7\x45\xf8\x20\x00\x00\x00'              # stride 0x20
        code += b'\xc7\x45\xf0\xe8\x88\x00\x00'              # usage GL_DYNAMIC_DRAW
        code += b'\xb9\x00\x10\x60\x00'                      # mov ecx, 0x601000
        here = BASE+len(code)
        code += b'\xe8'+struct.pack('<i', 0x00402000-(here+5))+b'\xc9\xc3'
        params = frame.creation_parameters(text_of(code), BASE)
        self.assertEqual(params, {'creator': hex(BASE), 'helper': '0x402000', 'object': '0x601000', 'flags': 0xb,
                                  'usage': 'GL_DYNAMIC_DRAW', 'size': 0x140, 'stride': 0x20})

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_private_frame_map(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        wine = Path(os.environ.get('MU_WINE_DLLS',
                                   ROOT/'evidence/client-frame/wine-dlls/usr/lib/i386-linux-gnu/wine/i386-windows'))
        command = [sys.executable, str(ROOT/'scripts/client_frame_static.py'), '--text', str(text), '--data', str(data),
                   '--wine-dlls', str(wine)]
        game = os.environ.get('MU_GAME_ROOT')
        if game:
            command += ['--game-root', game]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'frame.json'
            subprocess.run(command+['--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        timing = report['timing_imports']
        self.assertEqual([s['function'] for s in timing['SwapBuffers']['call_sites']],
                         ['0x11e2c8c', '0x1851adc', '0x1851d39'])
        self.assertIn({'site': '0x185267a', 'function': '0x1851d39'}, timing['Sleep']['call_sites'])
        self.assertEqual(timing['timeBeginPeriod']['call_sites'], [{'site': '0x11864c4', 'function': '0x118648a'}])
        driver = report['frame_driver']
        self.assertTrue(all(c['match'] for c in driver['checks']+driver['dispatch_checks']))
        self.assertEqual([f['immediate'] for f in driver['cap_fields']+driver['logic_step_fields']], [40]*5)
        self.assertTrue(all(f['match'] for f in driver['cap_fields']+driver['logic_step_fields']))
        self.assertEqual(driver['cap_block']['sha256'], '37978e180c2e7f1dd9d0760f44b0e30ab9de431699ae982c1b8b1b2ceca52e14')
        self.assertEqual((driver['frame_driver_callers'], driver['dispatcher_callers']),
                         (['0x1859e4b'], ['0x120ef38', '0x120ef54']))
        begin = report['glbegin']
        self.assertEqual(begin['modes'], {'GL_QUADS': 27, 'GL_LINE_STRIP': 1, 'GL_TRIANGLE_FAN': 24,
                                          'GL_TRIANGLES': 10, 'GL_LINES': 6})
        self.assertEqual(begin['unlabelled'], [])
        self.assertEqual(begin['categories']['GL_TRIANGLE_FAN'],
                         {'3d-misc': 1, '2d': 11, '3d-effect': 2, 'terrain': 9, 'terrain-decal': 1})
        sites = {s['site']: s for s in begin['hot_sites']}
        self.assertEqual(sites['0x16cfaad']['return_address'], '0x16cfab3')
        self.assertEqual((sites['0x184deea']['raw_callers'], sites['0x184c90e']['raw_callers']), (243, 445))
        vbo = report['vbo']
        self.assertEqual(vbo['stream_buffers'], [
            {'creator': '0xa6fe5d', 'helper': '0xa92497', 'object': '0x1d1e2c8', 'flags': 11,
             'usage': 'GL_STREAM_DRAW', 'size': 144, 'stride': 36},
            {'creator': '0xa8a3ea', 'helper': '0xa92497', 'object': '0x1d1e6f8', 'flags': 11,
             'usage': 'GL_STREAM_DRAW', 'size': 144000, 'stride': 36}])
        self.assertEqual([s['arguments'] for s in vbo['pointer_slots']['0x1a7cb80']['sites']],
                         [['0x8892', '0', '0x90', 'eax'], ['0x8892', '0', 'eax', 'dword ptr [ebp - 0x20]']])
        if game:
            files = report['files']
            self.assertEqual((files['cap_block_in_file'], files['cap_head_in_file']), (0, 0))
            self.assertTrue(files['hook_targets_in_igc'])


if __name__ == '__main__':
    unittest.main()
