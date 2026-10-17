"""Synthetic checks for scripts/client_render_static.py (CLIENT-SKIN-001).

No game bytes are used: x86 fixtures are short hand-assembled sequences and
the PE fixture is a minimal authored export table. The private pinned-input
check runs only with MU_RECOVERY_INTEGRATION=1.
"""
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


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


static = load('client_render_static')
common = load('model_hierarchy_common')


def call(source, target):
    return b'\xe8'+struct.pack('<i', target-source-5)


def minimal_pe(base, exports):
    """One-section PE32 with an export directory; exports maps name -> RVA."""
    section_rva, section_raw = 0x1000, 0x200
    names = sorted(exports)
    directory = 0
    functions = directory+40
    name_pointers = functions+4*len(names)
    ordinals = name_pointers+4*len(names)
    strings = ordinals+2*len(names)
    blob = bytearray(strings)
    text = b''
    offsets = []
    for name in names:
        offsets.append(strings+len(text))
        text += name.encode()+b'\0'
    blob += text
    struct.pack_into('<IIIII', blob, directory+20, len(names), len(names), section_rva+functions,
                     section_rva+name_pointers, section_rva+ordinals)
    for index, name in enumerate(names):
        struct.pack_into('<I', blob, functions+4*index, exports[name])
        struct.pack_into('<I', blob, name_pointers+4*index, section_rva+offsets[index])
        struct.pack_into('<H', blob, ordinals+2*index, index)
    image = bytearray(section_raw+len(blob))
    struct.pack_into('<I', image, 0x3c, 0x40)
    image[0x40:0x44] = b'PE\0\0'
    struct.pack_into('<H', image, 0x46, 1)          # sections
    struct.pack_into('<H', image, 0x54, 0xe0)       # optional header size
    struct.pack_into('<I', image, 0x58+28, base)    # image base
    struct.pack_into('<I', image, 0x58+96, section_rva)
    section = 0x58+0xe0
    struct.pack_into('<IIII', image, section+8, len(blob), section_rva, len(blob), section_raw)
    image[section_raw:] = blob
    return bytes(image)


class ExportNamingTests(unittest.TestCase):
    def test_slot_values_map_to_export_rvas(self):
        payload = minimal_pe(0x7a800000, {'glBegin': 0xabdf0, 'glEnd': 0xb00a0, 'wglDeleteContext': 0xab560})
        base, exports = static.pe_exports(payload)
        self.assertEqual(base, 0x7a800000)
        self.assertEqual(exports[0xabdf0], ['glBegin'])
        data = common.Region(0x01a7c000, struct.pack('<4I', 0x7a8ab560, 0x7a8abdf0, 0x7a8c0000, 0))
        slots = static.name_slots(data, 0x01a7c000, 0x01a7c010, payload)
        self.assertEqual([s['name'] for s in slots], ['wglDeleteContext', 'glBegin', None])
        # A relocated DLL is named against the observed base.
        data = common.Region(0x01a7c000, struct.pack('<2I', 0x003abdf0, 0))
        self.assertEqual(static.name_slots(data, 0x01a7c000, 0x01a7c008, payload, base=0x00300000)[0]['name'],
                         'glBegin')

    def test_non_pe_is_rejected(self):
        with self.assertRaises(ValueError):
            static.pe_exports(b'\0'*0x100)


class CallReadingTests(unittest.TestCase):
    BASE = 0x00401000

    def text(self, code):
        return static.Text(common.Region(self.BASE, code+b'\xcc'*32))

    def test_pose_call_arguments_follow_push_order_and_accessors(self):
        base = self.BASE
        code = bytearray(b'\xcc\x55\x8b\xec')               # padding, push ebp; mov ebp, esp
        code += b'\x6a\x01\x6a\x00'                          # push 1 (translate); push 0 (keep root)
        code += b'\x8b\x4d\x0c\x81\xc1\x70\x01\x00\x00'     # mov ecx,[ebp+0xc]; add ecx,0x170
        code += call(base+len(code), static.VECTOR)+b'\x50'  # call vector accessor; push eax (head)
        code += b'\x8b\x4d\x0c\x81\xc1\x64\x01\x00\x00'
        code += call(base+len(code), static.VECTOR)+b'\x50'  # angles
        code += b'\x8b\x45\x0c\x0f\xb7\x40\x2c\x50'          # movzx eax, word [eax+0x2c]; push eax
        code += b'\x8b\x45\x0c\x51\xf3\x0f\x10\x80\xd4\x00\x00\x00\xf3\x0f\x11\x04\x24'  # prior frame
        code += b'\x51\xf3\x0f\x10\x80\xd0\x00\x00\x00\xf3\x0f\x11\x04\x24'              # frame
        code += b'\x68'+struct.pack('<I', static.BONE_BUFFER)
        code += b'\x8b\x4d\xfc'                              # mov ecx,[ebp-4]
        site = base+len(code)
        code += call(site, static.POSE)+b'\xc9\xc3'
        text = self.text(bytes(code))
        self.assertEqual(text.raw_calls(static.POSE), [site])
        self.assertEqual(text.function_start(site), base+1)
        record = static.call_arguments(text, site, 8)
        self.assertEqual(record['arguments'], [hex(static.BONE_BUFFER), '[[ebp+0xc]+0xd0]', '[[ebp+0xc]+0xd4]',
                                               'u16[[ebp+0xc]+0x2c]', '([ebp+0xc])+0x164', '([ebp+0xc])+0x170',
                                               '0x0', '0x1'])
        self.assertEqual(record['ecx'], '[ebp-0x4]')
        self.assertEqual(static.classify_pose_call(record['arguments']),
                         {'output': 'bone-buffer', 'state': 'object-fields', 'head': 'object+0x170',
                          'keep_root': '0x0', 'translate': '0x1'})

    def test_function_start_rejects_a_prologue_whose_decode_returns_first(self):
        base = self.BASE
        code = bytearray(b'\x55\x8b\xec\xc3')               # earlier function returns
        code += b'\x90'*4+b'\x55\x8b\xec\x90'
        site = base+len(code)
        code += call(site, 0x00500000)
        text = self.text(bytes(code))
        self.assertEqual(text.function_start(site), base+8)
        code = bytearray(b'\x55\x8b\xec\xc3\x90')            # only a returning prologue precedes
        site = base+len(code)
        code += call(site, 0x00500000)
        self.assertIsNone(self.text(bytes(code)).function_start(site))

    def test_block_reading_stops_at_branch_targets(self):
        base = self.BASE
        code = bytearray(b'\x55\x8b\xec\x6a\x07\x74\x02\x6a\x08\x6a\x09')  # push 7; je +2; push 8; push 9
        site = base+len(code)
        code += call(site, 0x00500000)
        text = self.text(bytes(code))
        record = static.call_arguments(text, site, 1)
        self.assertEqual(record['arguments'], ['0x9'])
        self.assertEqual(record['block'], hex(base+9))     # the jump target starts the block

    def test_classification_of_bind_pose_and_computed_prior(self):
        self.assertEqual(static.classify_pose_call(['0x6fce398', '0.0', '0.0', '0x0', '&[ebp-0x28]', '&[ebp-0x28]',
                                                    '0x0', '0x0'])['state'], 'bind-pose')
        self.assertEqual(static.classify_pose_call(['0x6fce398', '[ebp-0x8]', 'float((int([ebp-0x8]))-1)', '0x0',
                                                    '0x1', '0x2', '0x0', '0x1'])['state'], 'prior-is-frame-minus-one')

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private pinned client captures')
    def test_private_render_path_map(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA', ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        wine = Path(os.environ.get('MU_WINE_DLLS', ROOT/'evidence/client-skinning/wine-dlls/usr/lib/i386-linux-gnu/wine/i386-windows'))
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'static.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/client_render_static.py'), '--text', str(text),
                            '--data', str(data), '--opengl32', str(wine/'opengl32.dll'), '--glu32', str(wine/'glu32.dll'),
                            '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        pose = report['pose_callers']
        self.assertEqual((pose['raw_candidates'], pose['synced'], pose['functions'], pose['widened']), (314, 314, 105, 0))
        self.assertEqual(pose['classes']['output'], {'bone-buffer': 300, 'other': 14})
        self.assertEqual(pose['classes']['state'], {'object-prior-computed-frame': 140, 'object-fields': 117,
                                                    'other': 26, 'prior-is-frame-minus-one': 19, 'bind-pose': 12})
        self.assertEqual(pose['classes']['keep_root'], {'0x0': 289, '0x1': 24, 'u8[[ebp+0x8]+0x39]': 1})
        tick = report['tick_callers']
        self.assertEqual((tick['raw_candidates'], tick['synced'], tick['functions']), (91, 91, 42))
        self.assertEqual(tick['argument_patterns'][1]['(ARG)+0xd4'], 68)
        self.assertEqual(report['imports']['opengl32_named'], 81)
        self.assertEqual(report['imports']['glu32_named'], 4)
        self.assertTrue(all(report['imports']['first_slot_is_static_import'].values()))
        self.assertEqual(report['glbegin_sites']['count'], 68)
        self.assertEqual(report['glbegin_sites']['modes'], {'GL_QUADS': 27, 'GL_LINE_STRIP': 1, 'GL_TRIANGLE_FAN': 24,
                                                            'GL_TRIANGLES': 10, 'GL_LINES': 6})
        self.assertEqual(report['consumers']['transform']['raw_calls'], 7)
        self.assertEqual(report['consumers']['render_mesh_default_buffers']['raw_calls'], 6361)
        calls = [event['call'] for event in report['render_mesh_gl']]
        begin = calls.index('glBegin')
        self.assertEqual(calls.count('glBegin'), 1)
        self.assertEqual(calls[-1], 'glEnd')
        self.assertEqual(report['render_mesh_gl'][begin]['recent_pushes'][0], '4')  # GL_TRIANGLES
        self.assertEqual(sorted(set(calls[begin+1:-1])), ['glColor3fv', 'glColor4f', 'glTexCoord2f', 'glVertex3fv'])


if __name__ == '__main__':
    unittest.main()
