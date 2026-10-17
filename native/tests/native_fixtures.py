"""Synthetic BMD models, envelopes and textures for the native viewer tests.

Everything here is authored: random-but-seeded geometry, bones and animation
tracks in the checked v10 layout (model-recovery/bmd10.py), wrapped in the
v12 (published rolling encoding, as in model-recovery/test_encrypted.py) and
v15 (LEA-256 ECB encryption with the published format key) envelopes. v14
uses the independent-oracle vectors in model-recovery/fixtures. Textures are
small generated TGA images in the observed OZT/OZB wrappers.
"""
import json
import math
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'model-recovery'))
import bmd_encrypted  # noqa: E402

MASK = 0xffffffff


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def name32(text):
    return text.encode('latin-1').ljust(32, b'\0')[:32]


def synthetic_layout(seed=1, *, meshes=3, bones=7, actions=3, keys=(5, 4, 1), four_corner=False,
                     texture_names=None):
    """Return a decoded v10 layout ('BMD\\x0a' + payload) with a deterministic model.

    Bone 3 is a dummy; bone 2 has a forward parent (bone 5), so it composes from
    the output slot as it was before this call; action 1 locks root positions.
    """
    g = random.Random(seed)
    usable = [b for b in range(bones) if b != 3]
    parents = {0: -1, 1: 0, 2: 5, 4: 1, 5: 0, 6: 4}
    chunks = [b'BMD\x0a', name32(f'synthetic{seed}.smd'), struct.pack('<HHH', meshes, bones, actions)]
    texture_names = texture_names or [f'tex{index}.tga' for index in range(meshes)]
    for mi in range(meshes):
        nv, nn, nt = g.randrange(6, 14), g.randrange(6, 14), g.randrange(4, 10)
        nf = g.randrange(6, 16)
        chunks.append(struct.pack('<hhhhh', nv, nn, nt, nf, mi))
        for _ in range(nv):
            chunks.append(struct.pack('<hhfff', g.choice(usable), 0, *[f32(g.uniform(-30, 30)) for _ in range(3)]))
        for _ in range(nn):
            v = [g.uniform(-1, 1) for _ in range(3)]
            length = math.sqrt(sum(x*x for x in v)) or 1.0
            chunks.append(struct.pack('<hhfffhh', g.choice(usable), 0, *[f32(x/length) for x in v],
                                      g.randrange(-1, nv), 0))
        for _ in range(nt):
            chunks.append(struct.pack('<ff', f32(g.uniform(-0.5, 1.5)), f32(g.uniform(-0.5, 1.5))))
        for fi in range(nf):
            corners = 4 if (four_corner and mi == 0 and fi == 1) else 3
            face = bytearray(64)
            face[0] = corners
            for offset, upper in ((2, nv), (10, nn), (18, nt)):
                values = [g.randrange(upper) for _ in range(corners)] + [-1]*(4-corners)
                struct.pack_into('<4h', face, offset, *values)
            for k in range(0x24, 64):   # bytes the mesh draw does not read
                face[k] = g.randrange(256)
            chunks.append(bytes(face))
        chunks.append(name32(texture_names[mi]))
    key_counts = [keys[a % len(keys)] for a in range(actions)]
    for a in range(actions):
        locked = 1 if a == 1 else 0
        chunks.append(struct.pack('<hB', key_counts[a], locked))
        if locked:
            for _ in range(key_counts[a]):
                chunks.append(struct.pack('<3f', *[f32(g.uniform(-5, 5)) for _ in range(3)]))
    for b in range(bones):
        if b == 3:
            chunks.append(b'\x01')
            continue
        chunks.append(b'\x00'+name32(f'bone{b}')+struct.pack('<h', parents[b]))
        for a in range(actions):
            for _ in range(key_counts[a]):
                chunks.append(struct.pack('<3f', *[f32(g.uniform(-20, 20)) for _ in range(3)]))
            for _ in range(key_counts[a]):
                chunks.append(struct.pack('<3f', *[f32(g.uniform(-math.pi, math.pi)) for _ in range(3)]))
    return b''.join(chunks)


def envelope_v12(layout):
    body = layout[4:]
    encoded = bytearray()
    previous = 0x5e
    for i, value in enumerate(body):
        byte = ((value+previous) & 255) ^ bmd_encrypted.MAP_KEY[i % 16]
        encoded.append(byte)
        previous = (byte+0x3d) & 255
    return b'BMD\x0c'+struct.pack('<I', len(encoded))+bytes(encoded)


def rol(value, bits):
    bits %= 32
    return ((value << bits) | (value >> ((32-bits) % 32))) & MASK


def ror(value, bits):
    return rol(value, 32-bits)


def lea_encrypt(plain, key=bmd_encrypted.FORMAT_KEY):
    keys = list(reversed(bmd_encrypted.round_keys(key)))
    out = bytearray(len(plain))
    for offset in range(0, len(plain), 16):
        x0, x1, x2, x3 = struct.unpack_from('<4I', plain, offset)
        for k0, k1, k2, k3, k4, k5 in keys:
            n0 = rol(((x0 ^ k0)+(x1 ^ k1)) & MASK, 9)
            n1 = ror(((x1 ^ k2)+(x2 ^ k3)) & MASK, 5)
            n2 = ror(((x2 ^ k4)+(x3 ^ k5)) & MASK, 3)
            x0, x1, x2, x3 = n0, n1, n2, x0
        struct.pack_into('<4I', out, offset, x0, x1, x2, x3)
    return bytes(out)


def envelope_v15(layout, pad_byte=0xa5):
    body = layout[4:]
    body += bytes([pad_byte])*((-len(body)) % 16)
    cipher = lea_encrypt(body)
    return b'BMD\x0f'+struct.pack('<I', len(cipher))+cipher


def v14_models():
    """Model envelopes from the independent v14 oracle vectors."""
    vectors = json.loads((ROOT/'model-recovery/fixtures/modulus-v14-vectors.json').read_text())
    result = []
    for vector in vectors['vectors']:
        if vector['kind'] != 'model':
            continue
        cipher = bytes.fromhex(vector['envelope_hex'])
        result.append((vector['name'], b'BMD\x0e'+struct.pack('<I', len(cipher))+cipher))
    return result


def tga(width, height, seed, *, alpha=True, rle=False, top_left=False):
    g = random.Random(seed)
    depth = 32 if alpha else 24
    header = struct.pack('<BBBHHBHHHHBB', 0, 0, 10 if rle else 2, 0, 0, 0, 0, 0, width, height, depth,
                         (8 if alpha else 0) | (0x20 if top_left else 0))
    pixels = []
    for y in range(height):
        for x in range(width):
            b, gr, r = (x*37+y*11+seed*5) & 255, (x*7+y*53+seed) & 255, g.randrange(256)
            pixels.append(bytes([b, gr, r] + ([g.choice([0, 128, 255])] if alpha else [])))
    if not rle:
        return header+b''.join(pixels)
    out = bytearray(header)
    index = 0
    while index < len(pixels):
        run = 1
        while index+run < len(pixels) and run < 128 and pixels[index+run] == pixels[index]:
            run += 1
        if run > 1:
            out.append(0x80 | (run-1))
            out += pixels[index]
            index += run
        else:
            raw = 1
            while index+raw < len(pixels) and raw < 128 and pixels[index+raw] != pixels[index+raw-1]:
                raw += 1
            out.append(raw-1)
            out += b''.join(pixels[index:index+raw])
            index += raw
    return bytes(out)


def ozt(payload, zero_field=False):
    return payload[:4]+(b'\0'*4 if zero_field else payload[:4])+payload[4:]


def bmp24(width, height, seed):
    stride = (width*3+3) & ~3
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            row += bytes([(x*13+seed) & 255, (y*29+seed) & 255, (x*y+seed) & 255])
        rows.append(bytes(row)+b'\0'*(stride-len(row)))
    pixels = b''.join(rows)
    header = b'BM'+struct.pack('<IHHI', 54+len(pixels), 0, 0, 54)
    info = struct.pack('<IiiHHIIiiII', 40, width, height, 1, 24, 0, len(pixels), 2835, 2835, 0, 0)
    return header+info+pixels


def ozb(payload):
    return payload[:4]+payload


def write_textured_model(directory, seed=1, *, version=10, four_corner=False, names=None):
    """Writes a synthetic model plus OZT textures for its meshes; returns the model path."""
    directory = Path(directory)
    names = names or ['skin.tga', 'cloth.tga', 'metal.tga']
    layout = synthetic_layout(seed, four_corner=four_corner, texture_names=names)
    raw = {10: lambda: layout, 12: lambda: envelope_v12(layout), 15: lambda: envelope_v15(layout)}[version]()
    path = directory/f'synthetic{seed}_v{version}.bmd'
    path.write_bytes(raw)
    for index, name in enumerate(names):
        stem = name.rsplit('.', 1)[0]
        payload = tga(8 << (index % 2), 8, seed*10+index, alpha=index != 1, rle=index == 2, top_left=index == 0)
        (directory/f'{stem.upper() if index == 1 else stem}.OZT').write_bytes(ozt(payload))
    return path


def character_layout(seed, *, bones, actions=1, keys=(1,), meshes=0, mesh_bones=None, dummies=(),
                     texture_prefix='part'):
    """Decoded v10 layout for character tests (NATIVE-CHAR-001).

    A Player-style skeleton (meshes=0, many bones and actions) or a part/item
    model whose vertices and normals reference bones of the shared skeleton
    (mesh_bones: bone indices to draw from; default every non-dummy bone).
    Parents point at a random earlier non-dummy bone (bone 0 is the root).
    """
    g = random.Random(seed)
    usable = [b for b in range(bones) if b not in dummies]
    mesh_bones = mesh_bones or usable
    chunks = [b'BMD\x0a', name32(f'character{seed}.smd'), struct.pack('<HHH', meshes, bones, actions)]
    for mi in range(meshes):
        nv, nn, nt = g.randrange(8, 20), g.randrange(8, 20), g.randrange(4, 10)
        nf = g.randrange(8, 20)
        chunks.append(struct.pack('<hhhhh', nv, nn, nt, nf, mi))
        for _ in range(nv):
            chunks.append(struct.pack('<hhfff', g.choice(mesh_bones), 0, *[f32(g.uniform(-25, 25)) for _ in range(3)]))
        for _ in range(nn):
            v = [g.uniform(-1, 1) for _ in range(3)]
            length = math.sqrt(sum(x*x for x in v)) or 1.0
            chunks.append(struct.pack('<hhfffhh', g.choice(mesh_bones), 0, *[f32(x/length) for x in v],
                                      g.randrange(nv), 0))
        for _ in range(nt):
            chunks.append(struct.pack('<ff', f32(g.uniform(0, 1)), f32(g.uniform(0, 1))))
        for _ in range(nf):
            face = bytearray(64)
            face[0] = 3
            for offset, upper in ((2, nv), (10, nn), (18, nt)):
                struct.pack_into('<4h', face, offset, *([g.randrange(upper) for _ in range(3)] + [-1]))
            chunks.append(bytes(face))
        chunks.append(name32(f'{texture_prefix}{mi}.tga'))
    key_counts = [keys[a % len(keys)] for a in range(actions)]
    for a in range(actions):
        chunks.append(struct.pack('<hB', key_counts[a], 0))
    for b in range(bones):
        if b in dummies:
            chunks.append(b'\x01')
            continue
        parent = -1 if b == 0 else g.choice([p for p in usable if p < b])
        chunks.append(b'\x00'+name32(f'cbone{b}')+struct.pack('<h', parent))
        for a in range(actions):
            for _ in range(key_counts[a]):
                chunks.append(struct.pack('<3f', *[f32(g.uniform(-15, 15)) for _ in range(3)]))
            for _ in range(key_counts[a]):
                chunks.append(struct.pack('<3f', *[f32(g.uniform(-math.pi, math.pi)) for _ in range(3)]))
    return b''.join(chunks)
