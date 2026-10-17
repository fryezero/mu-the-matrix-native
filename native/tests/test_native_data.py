"""Native data-table tool (NATIVE-DATA-001/002) checks.

Portable: every table is authored here and encoded with an independent Python
model of the client codecs, then decoded and dumped by native/build/mu-data.
Private (MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT): every catalogued
installed table decodes with status ok, the Item.bmd model list is complete,
and Lang.mpr lists its package directory. Decoded output stays in a temporary
directory.
"""
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
TOOL = NATIVE/'build/mu-data'
KEY3 = bytes((0xfc, 0xcf, 0xab))
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


def xor3(data):
    return bytes(b ^ KEY3[i % 3] for i, b in enumerate(data))


def checksum(data, key):
    result = (key << 9) & 0xffffffff
    for offset in range(0, len(data)-3, 4):
        word = struct.unpack_from('<I', data, offset)[0]
        result = result ^ word if ((offset >> 2)+key) % 2 == 0 else (result+word) & 0xffffffff
        if offset % 16 == 0:
            result = (((key+result) & 0xffffffff) >> (((offset >> 2) % 8)+1)) ^ result
    return result


def item_record(code, folder, file, name, fill=0):
    record = bytearray([fill])*708
    struct.pack_into('<IHH', record, 0, code, code // 512, code % 512)
    record[8:268] = folder.ljust(260, b'\0')
    record[268:528] = file.ljust(260, b'\0')
    record[528:592] = name.ljust(64, b'\0')
    record[0x250] = 7
    struct.pack_into('<H', record, 0x254, 0x1234)
    struct.pack_into('<I', record, 0x270, 0xdeadbeef)
    record[0x268] = 20          # durability
    record[0x291:0x2a1] = bytes(range(1, 17))
    record[0x2ab] = 1           # can_warehouse
    return bytes(record)


def item_file(records):
    payload = b''.join(xor3(r) for r in records)
    return struct.pack('<I', len(records))+payload+struct.pack('<I', checksum(payload, 0xe2f1))


def run(*args, check=True):
    result = subprocess.run([str(TOOL), *[str(a) for a in args]], capture_output=True)
    if check and result.returncode:
        raise AssertionError(result.stderr.decode())
    return result


class NativeDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-data'], check=True, capture_output=True)
        cls.folder = tempfile.TemporaryDirectory()
        cls.root = Path(cls.folder.name)
        (cls.root/'Data/Local').mkdir(parents=True)
        cls.records = [item_record(0, b'Data\\Item\\', b'sword01.bmd', b'Test Sword'),
                       item_record(513, b'Data\\Item\\', b'axe02.bmd', b'Caf\xe9 "Axe"'),
                       item_record(13000, b'Data\\Item\\', b'far.bmd', b'Far'),
                       item_record(0, b'Data\\Item\\', b'duplicate.bmd', b'Dup')]
        (cls.root/'Data/Local/Item.bmd').write_bytes(item_file(cls.records))

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_item_models_and_lookup(self):
        out = json.loads(run('item-models', self.root/'Data/Local/Item.bmd', '--json').stdout)
        self.assertEqual((out['model_base'], out['model_limit']), (0xae6, 0x3af6))
        items = out['items']
        self.assertEqual([i['code'] for i in items], [0, 513, 13000, 0])
        self.assertEqual(items[1], {'code': 513, 'section': 1, 'index': 1, 'model_index': 513+0xae6, 'in_range': True,
                                    'folder': 'Data\\Item\\', 'file': 'axe02.bmd',
                                    'texture_folder': 'Data\\Item\\Texture\\', 'name': 'Café "Axe"'})
        self.assertFalse(items[2]['in_range'])
        path = self.root/'Data/Local/Item.bmd'
        self.assertEqual(run('model', path, 0xae6).stdout.decode().split()[:2], ['load', '2790'])
        self.assertIn('Data\\Item\\sword01.bmd', run('model', path, 0xae6).stdout.decode())  # first record wins
        self.assertEqual(run('model', path, 5).stdout.decode().strip(), 'empty 5')
        self.assertEqual(run('model', path, 0x3af7).stdout.decode().strip(), 'null 15095')
        self.assertEqual(run('model', path, -1).stdout.decode().strip(), 'null -1')
        self.assertEqual(run('model', path, 13000+0xae6).stdout.decode().strip(), 'null 15790')

    def test_item_dump_fields(self):
        out = json.loads(run('dump', self.root/'Data/Local/Item.bmd').stdout)
        self.assertEqual((out['status'], out['records'], out['units'], out['checksum']['key']), ('ok', 4, 4, '0xe2f1'))
        item = out['items'][0]
        a = item['attributes']
        self.assertEqual((a['kind_a'], a['level'], a['magic_power'], a['durability'], a['can_warehouse']),
                         (7, 0x1234, 0xdeadbeef, 20, 1))
        self.assertEqual(a['require_class'], list(range(1, 17)))
        self.assertEqual(a['resistance'], [0]*7)
        self.assertEqual(list(a)[:3], ['kind_a', 'kind_b', 'type'])
        self.assertEqual(len(a), 52)  # 50 scalars + require_class[16] + resistance[7]
        self.assertEqual(item['unnamed'], {})  # gaps are reported only when nonzero
        self.assertEqual(out['items'][2]['code'], 13000)

    def test_item_derived_values(self):
        lines = run('item', self.root/'Data/Local/Item.bmd', 0).stdout.decode().splitlines()
        item, derived = json.loads(lines[0]), json.loads(lines[1])
        self.assertEqual(item['file'], 'sword01.bmd')  # first record for a repeated code
        # client 0x00ccc5b0 table: +L (1-4), +2L-4 (5-9), +2L-4+(L-9)(L-8)/2 (10-15); +15 excellent, +20 ancient
        self.assertEqual(derived['max_durability']['plain'],
                         [20, 21, 22, 23, 24, 26, 28, 30, 32, 34, 37, 41, 46, 52, 59, 67])
        self.assertEqual(derived['max_durability']['excellent'][0], 35)
        self.assertEqual(derived['max_durability']['ancient'][15], 87)
        self.assertEqual((derived['store_ban'], derived['repair_ban']), (0, 1))
        self.assertEqual(run('item', self.root/'Data/Local/Item.bmd', 99, check=False).returncode, 1)

    def test_layout_catalog_and_named_tables(self):
        layouts = {l['file']: l for l in json.loads(run('layouts').stdout)['layouts']}
        self.assertIn('itemtooltiptext.bmd', layouts)
        for layout in layouts.values():
            for f in layout['fields']:
                self.assertIn(f['evidence'], ('consumer', 'layout', 'data'))
                self.assertLessEqual(f['offset'], layout['record_size'])
            self.assertTrue(layout['fields'])
        item = {f['name']: f for f in layouts['item.bmd']['fields']}
        self.assertEqual((item['require_class']['offset'], item['require_class']['count']), (0x291, 16))
        self.assertEqual(item['field_2b9']['evidence'], 'layout')
        # a counted tooltip text table with the 0x00f1600f record codec and named fields
        records = []
        for i, (text, kind) in enumerate([(b'Attack speed: %d', 101), (b'Plain line', -1)]):
            record = bytearray(260)
            struct.pack_into('<H', record, 0, i)
            record[2:2+len(text)] = text
            struct.pack_into('<h', record, 0x102, kind)
            records.append(bytes(record))
        payload = b''.join(bytes(b ^ KEY3[k % 3] ^ 0xf1 for k, b in enumerate(r)) for r in records)
        image = struct.pack('<I', 2)+payload+struct.pack('<I', checksum(payload, 0xe2f1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'itemtooltiptext.bmd'
            path.write_bytes(image)
            data = json.loads(run('dump', path).stdout)['data']
            self.assertEqual([d['fields'] for d in data], [{'id': 0, 'text': 'Attack speed: %d', 'type': 101},
                                                           {'id': 1, 'text': 'Plain line', 'type': -1}])
            # a fixed unit holding several layout records is split (JewelOfHarmonyOption: 750 x 180)
            unit = bytearray(135000)
            struct.pack_into('<i60si14i14i', unit, 180, 2, b'Option', 0, *range(14), *range(100, 114))
            unit[200*180+0x45] = 0x5a  # high byte of level_value[0]
            harmony = Path(folder)/'JewelOfHarmonyOption.bmd'
            harmony.write_bytes(xor3(bytes(unit)))
            data = json.loads(run('dump', harmony).stdout)['data']
            self.assertEqual(len(data), 750)
            self.assertEqual(data[1]['fields']['name'], 'Option')
            self.assertEqual(data[1]['fields']['level_value'], list(range(14)))
            self.assertEqual(data[1]['fields']['zen'][-1], 113)
            self.assertEqual(data[200]['unnamed'], {})
            self.assertEqual(data[200]['fields']['level_value'][0], 0x5a00)

    def test_corrupt_and_unknown(self):
        bad = bytearray(item_file(self.records))
        bad[-2] ^= 0x40
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'item.bmd'
            path.write_bytes(bytes(bad))
            result = run('dump', path, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['status'], 'bad-checksum')
            other = Path(folder)/'notatable.bin'
            other.write_bytes(b'1234')
            self.assertEqual(run('dump', other, check=False).returncode, 2)
            self.assertEqual(run('decode', path, check=False).returncode, 2)  # --out required

    def test_words_map_lists_and_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            words = Path(folder)/'QuestWords.bmd'
            texts = [b'Hello', b'', b'World!\0']
            words.write_bytes(b''.join(xor3(struct.pack('<IH', i+1, len(t)))+xor3(t) for i, t in enumerate(texts)))
            out = json.loads(run('dump', words).stdout)
            self.assertEqual(out['data'], [{'id': 1, 'text': 'Hello'}, {'id': 2, 'text': ''}, {'id': 3, 'text': 'World!'}])
            lists = Path(folder)/'mapcharacters.bmd'
            plain = struct.pack('<5I', 3, 2, 10, 11, 4)+struct.pack('<I', 0)
            lists.write_bytes(b''.join(xor3(plain[i:i+4]) for i in range(0, len(plain), 4)))
            out = json.loads(run('dump', lists).stdout)
            self.assertEqual(out['data'], [{'key': 3, 'values': [10, 11]}, {'key': 4, 'values': []}])
            target = Path(folder)/'decoded.bin'
            run('decode', lists, '--out', target)
            self.assertEqual(target.read_bytes(), plain)

    def test_package_directory(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('\\Text(Test).txt', 'synthetic text\n'*20)
            archive.writestr('\\Gate.txt', '1 2 3\n')
        body = buffer.getvalue()
        encoded = bytes(b ^ KEY3[i % 3] ^ 0xdc for i, b in enumerate(body))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'Lang.mpr'
            path.write_bytes(encoded+struct.pack('<I', checksum(encoded, 0x12dc)))
            out = json.loads(run('mpr', path).stdout)
            self.assertEqual(out['entry_count'], 2)
            self.assertEqual([e['name'] for e in out['entries']], ['\\Text(Test).txt', '\\Gate.txt'])
            self.assertEqual(out['entries'][0]['size'], 15*20)
            self.assertFalse(out['entries'][0]['encrypted'])

    def test_list(self):
        result = run('list')
        self.assertIn(b'item.bmd', result.stdout)
        result = run('list', self.root, check=False)
        text = result.stdout.decode()
        self.assertIn('ok bytes=', text)
        self.assertIn('absent', text)

    @unittest.skipUnless(PRIVATE and os.environ.get('MU_GAME_ROOT'), 'private installation')
    def test_private_installed_tables(self):
        root = Path(os.environ['MU_GAME_ROOT'])
        result = run('list', root, check=False)
        lines = [l for l in result.stdout.decode().splitlines()[1:] if l.strip()]
        self.assertGreaterEqual(len(lines), 44)
        self.assertTrue(all(' ok bytes=' in l for l in lines), result.stdout.decode())
        item = next(p for p in (root/'Data/Local').iterdir() if p.name.lower() == 'item.bmd')
        models = json.loads(run('item-models', item, '--json').stdout)
        self.assertGreater(len(models['items']), 1000)
        self.assertTrue(all(i['in_range'] for i in models['items']))
        package = next(p for p in (root/'Data').iterdir() if p.name.lower() == 'lang.mpr')
        self.assertGreater(json.loads(run('mpr', package).stdout)['entry_count'], 50)


if __name__ == '__main__':
    unittest.main()
