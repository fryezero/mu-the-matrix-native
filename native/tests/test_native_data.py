"""Native data-table tool (NATIVE-DATA-001) checks.

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
        self.assertEqual((item['fields']['0x250'], item['fields']['0x254'], item['fields']['0x270']),
                         (7, 0x1234, 0xdeadbeef))
        self.assertEqual(set(item['uninitialized']), {'0x252', '0x257', '0x261', '0x269', '0x26d', '0x289',
                                                      '0x291', '0x2aa', '0x2b0', '0x2bb', '0x2c2'})
        self.assertEqual(item['uninitialized']['0x291'], '00'*24)

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
