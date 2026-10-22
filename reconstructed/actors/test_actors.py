"""Checks for the authored actor routines (NATIVE-ACTOR-001).

Portable: worked examples of OpenMonsterModel 0x0180b0f4 (mu_monster_open),
SetAction 0x012affa4, the unarmed stop action 0x0139d6da and the character
animation step 0x013960d2 on synthetic client memory, each also checked
against the independent Python model in scripts/validate_actors.py where one
exists; integrity of the generated tables; refusal of unpinned text.
Private (MU_RECOVERY_INTEGRATION=1): the Unicorn comparison against the
client's instructions (scripts/validate_actors.py).
"""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUFFIX = 'dylib' if sys.platform == 'darwin' else 'so'


def load_validator():
    sys.path.insert(0, str(ROOT/'scripts'))
    spec = importlib.util.spec_from_file_location('validate_actors', ROOT/'scripts/validate_actors.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


class ActorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(HERE)], check=True, capture_output=True)
        cls.v = load_validator()
        cls.authored = cls.v.Authored(HERE/f'libactors.{SUFFIX}')
        cls.lib = cls.authored.handle

    # ------------------------------------------------------------------
    def open_monster(self, type_, **fixture):
        case = self.v.monster_case('t', type_, **fixture)
        mine = self.authored.run_open(case)
        lifted = {type_: {'ops': self.static_ops(type_)}}
        model = self.v.python_open(case, lifted)
        self.assertEqual(mine['status'], model['status'])
        self.assertEqual(mine['regions'], model['regions'])
        return case, mine

    def static_ops(self, type_):
        """The generated table, decoded back to the lifter's operation tuples."""
        count = ctypes.c_uint32()
        self.lib.mu_monster_type_ops.restype = ctypes.c_void_p
        self.lib.mu_monster_type_ops.argtypes = [ctypes.c_int32, ctypes.POINTER(ctypes.c_uint32)]
        address = self.lib.mu_monster_type_ops(type_, ctypes.byref(count))

        class Op(ctypes.Structure):
            _fields_ = [('kind', ctypes.c_uint8), ('model', ctypes.c_int16), ('action', ctypes.c_uint8),
                        ('offset', ctypes.c_uint8), ('value', ctypes.c_uint32)]
        ops = []
        own = type_+0x7a5
        for index in range(count.value):
            op = Op.from_address(address+index*ctypes.sizeof(Op))
            model = own+op.model
            if op.kind == 1:
                ops.append(('speed', model, op.action, op.value))
            elif op.kind == 2:
                ops.append(('loop', model, op.action, op.value))
            elif op.kind == 3:
                ops.append(('action_speed', model, op.action, op.value))
            elif op.kind in (4, 5):
                ops.append(('raw', model, op.action, op.offset, 'u32' if op.kind == 4 else 'u8', op.value))
            else:
                ops.append(('field', model, op.offset, 'u32' if op.kind == 6 else 'u8', op.value))
        return ops

    def speeds(self, regions, slot=0, count=8):
        data = regions[f'actions{slot}']
        return [struct.unpack_from('<f', data, 16*a+4)[0] for a in range(count)]

    def test_monster_defaults_and_loop(self):
        case, mine = self.open_monster(0, actions=12)
        self.assertEqual(self.speeds(mine['regions'])[:7], [f32(x) for x in (0.25, 0.2, 0.34, 0.33, 0.33, 0.5, 0.55)])
        self.assertEqual(mine['regions']['actions0'][16*6], 1)   # die action loops (stop flag)
        self.assertEqual(mine['calls'][0], ('access', 0x7a5, 'Data\\Monster\\', 'Monster', 1))
        self.assertEqual(mine['calls'][1], ('texture', 0x7a5, 'Monster\\', 0x2901, 0x2600))

    def test_type_scale_rules_and_table_override(self):
        _, mine = self.open_monster(3, actions=12)
        self.assertEqual(self.speeds(mine['regions'])[0], f32(f32(0.25)*f32(1.2)))
        self.assertEqual(self.speeds(mine['regions'])[6], f32(0.55))          # action 6 is not scaled
        _, mine = self.open_monster(2, actions=12)
        self.assertEqual(self.speeds(mine['regions'])[2], f32(0.7))           # switch 0x0180cd7c case 2

    def test_checked_and_unchecked_stores(self):
        case, mine = self.open_monster(2, actions=2)
        original = case['regions'][1].data
        speeds = self.speeds(mine['regions'])
        self.assertEqual(speeds[:2], [f32(0.25), f32(0.2)])
        self.assertEqual(speeds[2], f32(0.7))   # direct store past the action count, as in the client
        self.assertEqual(mine['regions']['actions0'][16*3+4:16*3+8], original[16*3+4:16*3+8])

    def test_early_returns_and_client_fault(self):
        for fixture in ({'preloaded': (0, 2)}, {'preloaded': (1, 0)}, {'meshes': 0}):
            case, mine = self.open_monster(3, **fixture)
            self.assertEqual(mine['regions']['actions0'], bytes(case['regions'][1].data))
        _, mine = self.open_monster(49, actions=3)   # GetAction(6) on a 3-action model: null pointer in the client
        self.assertEqual(mine['status'], 3)

    def test_texture_directory_by_world(self):
        for type_, world, expected in ((0x46, 0x12, 'Npc\\'), (0x48, 0x61, 'Npc\\'), (0x49, 0x12, 'Monster\\'),
                                       (0x4a, 30, 'Object31\\'), (0x4a, 0, 'Monster\\')):
            _, mine = self.open_monster(type_, world=world)
            self.assertEqual(mine['calls'][1][2], expected, (type_, world))

    def test_negative_controls_differ(self):
        case = self.v.monster_case('t', 2, actions=2)
        lifted = {2: {'ops': self.static_ops(2)}}
        faithful = self.v.python_open(case, lifted)
        self.assertNotEqual(faithful['regions'], self.v.python_open(case, lifted, 'checked-direct')['regions'])
        self.assertNotEqual(faithful['regions'], self.v.python_open(case, lifted, 'unchecked-defaults')['regions'])

    # ------------------------------------------------------------------
    def test_set_action(self):
        v = self.v
        for case in v.set_action_cases(200):
            regions = {r.name: bytearray(r.data) for r in case['regions']}
            obj = regions['object']
            count = struct.unpack_from('<h', regions['model'], 0x26)[0]
            current = struct.unpack_from('<H', obj, 0x2a)[0]
            expected = bytearray(obj)
            if case['present'] and case['action'] < count and current != case['action']:
                struct.pack_into('<H', expected, 0x2c, current)
                expected[0xd4:0xd8] = obj[0xd0:0xd4]
                struct.pack_into('<H', expected, 0x2a, case['action'] & 0xffff)
                struct.pack_into('<I', expected, 0xd0, 0)
            buffers, memory, images = self.authored.memory(case['regions'])
            callback = ctypes.CFUNCTYPE(ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32)(
                lambda c, index, case=case: v.MODEL if case['present'] and index == case['type'] else 0)
            function = self.lib.mu_set_action
            function.argtypes = [ctypes.POINTER(self.authored.Memory), ctypes.c_uint32, ctypes.c_int32,
                                 type(callback), ctypes.c_void_p]
            self.assertEqual(function(ctypes.byref(memory), v.OBJECT, case['action'], callback, None), 0)
            self.assertEqual(bytes(buffers[0][1]), bytes(expected), case['label'])

    def test_unarmed_stop_action(self):
        function = self.lib.mu_player_unarmed_stop_action
        rand_type = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p)
        function.argtypes = [ctypes.c_uint8, ctypes.c_int32, rand_type, ctypes.c_void_p]
        function.restype = ctypes.c_int32
        zero, other = rand_type(lambda c: 40), rand_type(lambda c: 7)
        expected = {0: 1, 1: 1, 2: 2, 3: 1, 4: 1, 5: 3, 6: 1, 7: 5, 8: 6, 9: 6, 10: 1, 11: 1, 12: 2, 13: 1, 14: 6, 15: 8}
        for base, value in expected.items():
            self.assertEqual(function(base | 0x30, 0, other, None), value, base)
        self.assertEqual(function(10, 0, zero, None), 0x1f)
        self.assertEqual(function(15, 0, zero, None), 9)
        for world in (0x12, 0x17, 0x35, 0x61):
            self.assertEqual(function(5, world, zero, None), 1)
            self.assertEqual(function(15, world, zero, None), 8)

    def test_character_step_examples(self):
        v = self.v
        import random
        generator = random.Random(5)
        seen = set()
        for type_, action in ((0x7a5, 2), (0x13f, 2), (0xa52, 3), (0x7e5, 6), (0xa91, 0x9f), (0x7fc, 6)):
            case = v.step_case('x', generator, type_=type_, action=action)
            case['buffs'] = set()
            case['model_present'] = True
            mine = v.run_authored_step(self.authored, case)
            self.assertEqual(mine['status'], 0)
            seen.add((type_, mine['speed']))
        self.assertEqual(len(seen), 6)
        case = v.step_case('buffed', generator, type_=0x7a5, action=2)
        case['buffs'] = {0x48}
        case['model_present'] = True
        mine = v.run_authored_step(self.authored, case)
        self.assertEqual(mine['al'], 0)
        self.assertEqual(mine['calls'], [('buff', 0x3d), ('buff', 0x48)])

    # ------------------------------------------------------------------
    def test_tables(self):
        lib = self.lib

        class Slot(ctypes.Structure):
            _fields_ = [('type', ctypes.c_uint16), ('level', ctypes.c_uint8)]

        class Row(ctypes.Structure):
            _fields_ = [('server_class', ctypes.c_uint16), ('kind', ctypes.c_uint8), ('model', ctypes.c_uint16),
                        ('opened', ctypes.c_uint16), ('scale_bits', ctypes.c_uint32), ('slots', Slot*9),
                        ('class_byte', ctypes.c_uint8)]
        lib.mu_monster_class_find.restype = ctypes.POINTER(Row)
        lib.mu_monster_class_find.argtypes = [ctypes.c_uint32]
        row = lib.mu_monster_class_find(0).contents
        self.assertEqual((row.kind, row.model, row.opened), (1, 0x7a5, 0))
        self.assertEqual(struct.unpack('<f', struct.pack('<I', row.scale_bits))[0], f32(0.8))
        row = lib.mu_monster_class_find(3).contents
        self.assertEqual((row.model, row.opened), (0x7ae, 9))
        self.assertFalse(lib.mu_monster_class_find(0xffff))
        out = ctypes.create_string_buffer(64)
        lib.mu_access_model_file.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int32, ctypes.c_char_p,
                                             ctypes.c_uint32]
        for number, expected in ((-1, b'D\\Name.bmd'), (3, b'D\\Name03.bmd'), (12, b'D\\Name12.bmd'),
                                 (-2, b'D\\Name0-2.bmd')):
            self.assertTrue(lib.mu_access_model_file(b'D\\', b'Name', number, out, 64))
            self.assertEqual(out.value, expected)
        self.assertEqual(self.authored.file_for(0), 'Data\\Monster\\Monster01.bmd')
        self.assertEqual(self.authored.file_for(150), 'Data\\Monster\\Monster151.bmd')
        self.assertIsNone(self.authored.file_for(0x259))
        lib.mu_player_action_speed.restype = ctypes.c_float
        lib.mu_player_action_speed.argtypes = [ctypes.c_int32]
        written = sum(1 for a in range(0x186) if lib.mu_player_action_speed(a) != 0)
        self.assertEqual(written, 213)
        self.assertEqual(lib.mu_player_action_speed(1), f32(0.28))
        lib.mu_player_pose_action.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint8, ctypes.c_int32]
        self.assertEqual(lib.mu_player_pose_action(0, 0, 2, 0), 2)      # elf unarmed stand
        self.assertEqual(lib.mu_player_pose_action(1, 0, 2, 0), 0x33)   # female walk
        self.assertEqual(lib.mu_player_pose_action(2, 1, 1, 0), 0x71)   # one-handed attack

    def test_generated_table_is_current_with_the_lifter_format(self):
        header = (HERE/'monster_open_table.h').read_text()
        self.assertIn('#define MU_MONSTER_TABLE_TYPES 601', header)
        self.assertIn('2bd5f2e9dfb68ae5a3c6b95c5c53be842aaa8d2666996238b3874f503fc93724', header)

    def test_refuses_unpinned_text(self):
        with tempfile.NamedTemporaryFile() as handle:
            handle.write(b'\0'*64)
            handle.flush()
            result = subprocess.run([sys.executable, str(ROOT/'scripts/validate_actors.py'), '--text', handle.name,
                                     '--data', handle.name], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('restored text', result.stderr)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1',
                         'Private actor instruction comparison is opt-in')
    def test_private_original_actor_instructions(self):
        text = Path(os.environ.get('MU_CLIENT_TEXT', ROOT/'evidence/x86-text-capture-09/client-text.bin'))
        data = Path(os.environ.get('MU_IMAGE_DATA',
                                   ROOT/'evidence/image-data-run10/data-capture-10/client-image-data.bin'))
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_actors.py'), '--text', str(text),
                            '--data', str(data), '--output', str(report), '--classes', '0x100'],
                           check=True, capture_output=True)
            result = json.loads(report.read_text())
        opener = result['monster_open']
        self.assertEqual(opener['matches'], opener['cases'])
        self.assertGreaterEqual(opener['cases'], 1276)
        self.assertTrue(all(opener['negative_controls'].values()))
        for key in ('character_step', 'set_action', 'unarmed_stop'):
            self.assertEqual(result[key]['matches'], result[key]['cases'], key)
        self.assertTrue(all(result['character_step']['branches'].values()))
        self.assertEqual(result['classes']['static_disagree'], 0)
        self.assertEqual(result['player_speeds']['written'], 213)


if __name__ == '__main__':
    unittest.main()
