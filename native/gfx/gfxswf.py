"""Readers for the client's Scaleform GFx interface files (NATIVE-GFX-001).

Independently written from the public SWF 10 file format specification and the
publicly documented Scaleform GFx exporter tags (tag codes 1000..1009).  No
client code or bytes are contained here.

File layers observed in `Data/Interface/GFx` (see docs/research/native-gfx.md):

* `*.ozg`: the ModulusCrypt envelope (the same 34-byte prefix and block-cipher
  windows as BMD v14, decoded by model-recovery/libmodulus) around a GFx movie
  whose header is `CFX` (zlib) or `GFX` (stored) instead of `CWS`/`FWS`.
* `*.ozd`: the same envelope around a DDS image.
* `*.swf`, `fonts/*.gfx`: plain (`CWS`/`FWS`/`CFX`/`GFX`) files.

The module offers: envelope decoding, movie decompression, a tag walker that
descends into sprites, decoders for the GFx extension tags, a small AVM1 (AS2)
scanner that recovers ExternalInterface/fscommand calls and member-function
names, DDS decoding (DXT1/3/5 and uncompressed 32-bit) and helpers to write a
standard SWF.
"""
from __future__ import annotations

import ctypes
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

TAG_NAMES = {
    0: 'End', 1: 'ShowFrame', 2: 'DefineShape', 4: 'PlaceObject', 5: 'RemoveObject', 6: 'DefineBits',
    7: 'DefineButton', 8: 'JPEGTables', 9: 'SetBackgroundColor', 10: 'DefineFont', 11: 'DefineText',
    12: 'DoAction', 13: 'DefineFontInfo', 14: 'DefineSound', 15: 'StartSound', 17: 'DefineButtonSound',
    18: 'SoundStreamHead', 19: 'SoundStreamBlock', 20: 'DefineBitsLossless', 21: 'DefineBitsJPEG2',
    22: 'DefineShape2', 23: 'DefineButtonCxform', 24: 'Protect', 26: 'PlaceObject2', 28: 'RemoveObject2',
    32: 'DefineShape3', 33: 'DefineText2', 34: 'DefineButton2', 35: 'DefineBitsJPEG3',
    36: 'DefineBitsLossless2', 37: 'DefineEditText', 39: 'DefineSprite', 41: 'ProductInfo',
    43: 'FrameLabel', 45: 'SoundStreamHead2', 46: 'DefineMorphShape', 48: 'DefineFont2',
    56: 'ExportAssets', 57: 'ImportAssets', 58: 'EnableDebugger', 59: 'DoInitAction',
    60: 'DefineVideoStream', 61: 'VideoFrame', 62: 'DefineFontInfo2', 63: 'DebugID',
    64: 'EnableDebugger2', 65: 'ScriptLimits', 66: 'SetTabIndex', 69: 'FileAttributes',
    70: 'PlaceObject3', 71: 'ImportAssets2', 73: 'DefineFontAlignZones', 74: 'CSMTextSettings',
    75: 'DefineFont3', 76: 'SymbolClass', 77: 'Metadata', 78: 'DefineScalingGrid', 72: 'DoABC',
    82: 'DoABC2', 83: 'DefineShape4', 84: 'DefineMorphShape2', 86: 'DefineSceneAndFrameLabelData',
    87: 'DefineBinaryData', 88: 'DefineFontName', 89: 'StartSound2', 90: 'DefineBitsJPEG4',
    91: 'DefineFont4', 93: 'EnableTelemetry', 94: 'PlaceObject4',
    # Scaleform GFx exporter extensions.
    1000: 'GFx:ExporterInfo', 1001: 'GFx:DefineExternalImage', 1002: 'GFx:FontTextureInfo',
    1003: 'GFx:DefineExternalGradient', 1004: 'GFx:DefineGradientMap', 1005: 'GFx:DefineCompactedFont',
    1006: 'GFx:DefineExternalSound', 1007: 'GFx:DefineExternalStreamSound', 1008: 'GFx:DefineSubImage',
    1009: 'GFx:DefineExternalImage2',
}

# Tags whose first u16 is the character id they define.
DEFINE_TAGS = {2, 6, 7, 10, 11, 14, 20, 21, 22, 32, 33, 34, 35, 36, 37, 39, 46, 48, 60, 75, 83, 84, 87, 90,
               91, 1001, 1003, 1005, 1008}

# Scaleform file-type constants as stored in the exporter tags.
GFX_BITMAP_FORMATS = {10: 'JPEG', 11: 'PNG', 12: 'GIF', 13: 'TGA', 14: 'DDS'}


class FormatError(ValueError):
    pass


# --------------------------------------------------------------------------- envelope

_MODULUS = None


def modulus_library():
    """Load model-recovery/libmodulus (built by `make -C model-recovery`)."""
    global _MODULUS
    if _MODULUS is None:
        name = 'libmodulus.dylib' if sys.platform == 'darwin' else 'libmodulus.so'
        path = REPO/'model-recovery'/name
        if not path.exists():
            raise FormatError(f'{path} is missing; run make -C model-recovery')
        lib = ctypes.CDLL(str(path))
        fn = lib.mu_modulus_decrypt
        fn.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t,
                       ctypes.POINTER(ctypes.c_size_t), ctypes.c_char_p, ctypes.c_size_t]
        fn.restype = ctypes.c_int
        _MODULUS = fn
    return _MODULUS


def open_envelope(data: bytes) -> bytes:
    """Undo the ModulusCrypt envelope (34-byte prefix) of an .ozg/.ozd file."""
    fn = modulus_library()
    out = ctypes.create_string_buffer(max(len(data), 1))
    written = ctypes.c_size_t()
    err = ctypes.create_string_buffer(256)
    if fn(data, len(data), out, len(data), ctypes.byref(written), err, 256):
        raise FormatError(err.value.decode(errors='replace'))
    return out.raw[:written.value]


def read_container(path: Path) -> tuple[str, bytes]:
    """Return (layer description, payload) for any file of the GFx directory."""
    raw = Path(path).read_bytes()
    if raw[:3] in (b'CFX', b'GFX', b'CWS', b'FWS', b'ZWS') or raw[:4] == b'DDS ':
        return 'plain', raw
    return 'modulus', open_envelope(raw)


# --------------------------------------------------------------------------- SWF

@dataclass
class Movie:
    signature: str
    version: int
    declared_length: int
    frame_rect: tuple
    frame_rate: float
    frame_count: int
    body: bytes            # uncompressed bytes after the 8-byte header
    tags_offset: int       # offset of the first tag inside body

    @property
    def gfx(self) -> bool:
        return self.signature in ('CFX', 'GFX')

    @property
    def width(self) -> float:
        return (self.frame_rect[1] - self.frame_rect[0]) / 20.0

    @property
    def height(self) -> float:
        return (self.frame_rect[3] - self.frame_rect[2]) / 20.0


class BitReader:
    def __init__(self, data: bytes, pos: int = 0):
        self.data, self.byte, self.bit = data, pos, 0

    def ub(self, n: int) -> int:
        v = 0
        for _ in range(n):
            if self.byte >= len(self.data):
                raise FormatError('bit read past end')
            v = (v << 1) | ((self.data[self.byte] >> (7 - self.bit)) & 1)
            self.bit += 1
            if self.bit == 8:
                self.bit, self.byte = 0, self.byte + 1
        return v

    def sb(self, n: int) -> int:
        v = self.ub(n)
        return v - (1 << n) if n and v & (1 << (n - 1)) else v

    def align(self) -> int:
        if self.bit:
            self.bit, self.byte = 0, self.byte + 1
        return self.byte


def read_rect(data: bytes, pos: int) -> tuple[tuple, int]:
    r = BitReader(data, pos)
    n = r.ub(5)
    rect = (r.sb(n), r.sb(n), r.sb(n), r.sb(n))
    return rect, r.align()


def parse_movie(data: bytes) -> Movie:
    sig = data[:3].decode('latin-1')
    if sig not in ('CFX', 'GFX', 'CWS', 'FWS'):
        raise FormatError(f'not a SWF/GFx movie (signature {data[:3]!r})')
    version, length = data[3], struct.unpack_from('<I', data, 4)[0]
    if sig in ('CFX', 'CWS'):
        try:
            body = zlib.decompress(data[8:])
        except zlib.error as exc:
            raise FormatError(f'zlib: {exc}') from exc
    else:
        body = data[8:]
    rect, pos = read_rect(body, 0)
    rate = struct.unpack_from('<H', body, pos)[0] / 256.0
    count = struct.unpack_from('<H', body, pos + 2)[0]
    return Movie(sig, version, length, rect, rate, count, body, pos + 4)


@dataclass
class Tag:
    code: int
    data: bytes
    depth: int = 0          # 0 = top level, 1 = inside a DefineSprite
    sprite: int | None = None

    @property
    def name(self) -> str:
        return TAG_NAMES.get(self.code, f'Unknown{self.code}')


def iter_tags(data: bytes, pos: int, end: int | None = None, depth: int = 0, sprite: int | None = None):
    end = len(data) if end is None else end
    while pos < end:
        if pos + 2 > end:
            raise FormatError('truncated tag header')
        hdr = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        code, length = hdr >> 6, hdr & 0x3f
        if length == 0x3f:
            length = struct.unpack_from('<I', data, pos)[0]
            pos += 4
        if pos + length > end:
            raise FormatError(f'tag {code} overruns its container')
        body = data[pos:pos + length]
        pos += length
        yield Tag(code, body, depth, sprite)
        if code == 39 and length >= 4:
            sid = struct.unpack_from('<H', body, 0)[0]
            yield from iter_tags(body, 4, len(body), depth + 1, sid)
        if code == 0 and depth > 0:
            return


def movie_tags(movie: Movie):
    return iter_tags(movie.body, movie.tags_offset)


def encode_tag(code: int, payload: bytes, force_long: bool = False) -> bytes:
    if len(payload) < 0x3f and not force_long:
        return struct.pack('<H', (code << 6) | len(payload)) + payload
    return struct.pack('<HI', (code << 6) | 0x3f, len(payload)) + payload


def write_swf(version: int, header_body: bytes, tags: bytes, compress: bool = True) -> bytes:
    """header_body = RECT + rate + count (exactly as read); tags = encoded tags."""
    body = header_body + tags
    length = 8 + len(body)
    if compress:
        return b'CWS' + bytes([version]) + struct.pack('<I', length) + zlib.compress(body, 9)
    return b'FWS' + bytes([version]) + struct.pack('<I', length) + body


# --------------------------------------------------------------------------- small readers

def cstring(data: bytes, pos: int) -> tuple[str, int]:
    end = data.index(b'\0', pos)
    return data[pos:end].decode('utf-8', errors='replace'), end + 1


def pstring(data: bytes, pos: int) -> tuple[str, int]:
    n = data[pos]
    return data[pos + 1:pos + 1 + n].decode('utf-8', errors='replace'), pos + 1 + n


def define_id(tag: Tag) -> int | None:
    if tag.code in DEFINE_TAGS and len(tag.data) >= 2:
        return struct.unpack_from('<H', tag.data, 0)[0]
    if tag.code == 1009 and len(tag.data) >= 4:
        return struct.unpack_from('<I', tag.data, 0)[0]
    return None


def parse_exporter_info(data: bytes) -> dict:
    version = struct.unpack_from('<H', data, 0)[0]
    pos, flags = 2, 0
    if version >= 0x10a:
        flags = struct.unpack_from('<I', data, pos)[0]
        pos += 4
    bitmap_format = struct.unpack_from('<H', data, pos)[0]
    prefix, pos = pstring(data, pos + 2)
    swf_name, pos = pstring(data, pos)
    code_offsets = 0
    if len(data) - pos >= 2:
        code_offsets = struct.unpack_from('<H', data, pos)[0]
    return {'version': f'0x{version:04x}', 'flags': flags, 'code_offsets': code_offsets,
            'flag_names': [n for b, n in ((1, 'glyph_textures'), (2, 'gradient_images'),
                                          (4, 'shape_stripping'), (8, 'compacted_fonts'),
                                          (16, 'strip_fonts')) if flags & b],
            'bitmap_format': GFX_BITMAP_FORMATS.get(bitmap_format, bitmap_format),
            'prefix': prefix, 'swf_name': swf_name, 'extra': len(data) - pos}


def parse_external_image(tag: Tag) -> dict:
    d = tag.data
    if tag.code == 1009:
        cid = struct.unpack_from('<I', d, 0)[0]
        pos = 4
    else:
        cid = struct.unpack_from('<H', d, 0)[0]
        pos = 2
    fmt, w, h = struct.unpack_from('<HHH', d, pos)
    pos += 6
    export_name, pos = pstring(d, pos)
    file_name, pos = pstring(d, pos)
    return {'id': cid, 'format': GFX_BITMAP_FORMATS.get(fmt, fmt), 'width': w, 'height': h,
            'export_name': export_name, 'file': file_name, 'extra': len(d) - pos}


def parse_sub_image(tag: Tag) -> dict:
    cid, image, x1, y1, x2, y2 = struct.unpack_from('<HHHHHH', tag.data, 0)
    return {'id': cid, 'image': image, 'rect': (x1, y1, x2, y2)}


def parse_font(tag: Tag) -> dict:
    """DefineFont2/3 header: id, flags, name, glyph count."""
    d = tag.data
    fid, flags = struct.unpack_from('<HB', d, 0)
    name, _ = pstring(d, 4)
    glyphs = struct.unpack_from('<H', d, 5 + d[4])[0]
    return {'id': fid, 'name': name.rstrip('\0'), 'glyphs': glyphs, 'bold': bool(flags & 1),
            'italic': bool(flags & 2), 'layout': bool(flags & 0x80), 'kind': tag.name}


def parse_compacted_font(tag: Tag) -> dict:
    """GFx DefineCompactedFont: id, then the font name as a NUL-terminated
    string (the client's six are "Slate Mobile"), then the compacted glyph
    data (not decoded).  Older readings took a length-prefixed name; both are
    accepted."""
    d = tag.data
    fid = struct.unpack_from('<H', d, 0)[0]
    name = ''
    end = d.find(b'\0', 2, 2 + 66)
    if end > 3 and all(32 <= c < 127 for c in d[2:end]):
        name = d[2:end].decode()
    else:
        for p in range(2, min(len(d) - 1, 16)):
            n = d[p]
            s = d[p + 1:p + 1 + n]
            if 2 <= n <= 64 and all(32 <= c < 127 for c in s):
                name = s.decode()
                break
    return {'id': fid, 'name': name, 'bytes': len(d), 'kind': tag.name}


def parse_edit_text(tag: Tag) -> dict:
    d = tag.data
    cid = struct.unpack_from('<H', d, 0)[0]
    _, pos = read_rect(d, 2)
    f1, f2 = d[pos], d[pos + 1]
    pos += 2
    out = {'id': cid, 'html': bool(f2 & 0x02), 'multiline': bool(f1 & 0x20), 'readonly': bool(f1 & 0x08),
           'embed_glyphs': bool(f2 & 0x01), 'device_font': bool(f2 & 0x01) is False}
    if f1 & 0x01:  # HasFont
        out['font'] = struct.unpack_from('<H', d, pos)[0]
        pos += 2
    if f2 & 0x80:  # HasFontClass
        out['font_class'], pos = cstring(d, pos)
    if f1 & 0x01 or f2 & 0x80:
        out['size'] = struct.unpack_from('<H', d, pos)[0] / 20.0
        pos += 2
    if f1 & 0x04:
        pos += 4
    if f1 & 0x02:
        pos += 2
    if f2 & 0x20:
        pos += 9
    out['variable'], pos = cstring(d, pos)
    if f1 & 0x80:
        out['text'], pos = cstring(d, pos)
    return out


def parse_assets(tag: Tag) -> list:
    """ExportAssets / SymbolClass: list of (id, name)."""
    d = tag.data
    n = struct.unpack_from('<H', d, 0)[0]
    pos, out = 2, []
    for _ in range(n):
        cid = struct.unpack_from('<H', d, pos)[0]
        name, pos = cstring(d, pos + 2)
        out.append((cid, name))
    return out


def parse_import_assets(tag: Tag) -> dict:
    d = tag.data
    url, pos = cstring(d, 0)
    if tag.code == 71:
        pos += 2
    n = struct.unpack_from('<H', d, pos)[0]
    pos += 2
    names = []
    for _ in range(n):
        cid = struct.unpack_from('<H', d, pos)[0]
        name, pos = cstring(d, pos + 2)
        names.append((cid, name))
    return {'url': url, 'assets': names}


# --------------------------------------------------------------------------- AVM1 scanner

class _Func:
    def __init__(self, name):
        self.name = name


class _Ref:
    def __init__(self, path):
        self.path = path


def _push_values(data: bytes):
    out, pos = [], 0
    while pos < len(data):
        t = data[pos]
        pos += 1
        if t == 0:
            s, pos = cstring(data, pos)
            out.append(s)
        elif t == 1:
            out.append(struct.unpack_from('<f', data, pos)[0]); pos += 4
        elif t in (2, 3):
            out.append(None)
        elif t == 4:
            out.append(_Ref(f'reg{data[pos]}')); pos += 1
        elif t == 5:
            out.append(bool(data[pos])); pos += 1
        elif t == 6:
            hi, lo = struct.unpack_from('<II', data, pos)
            out.append(struct.unpack('<d', struct.pack('<II', lo, hi))[0]); pos += 8
        elif t == 7:
            out.append(struct.unpack_from('<i', data, pos)[0]); pos += 4
        elif t == 8:
            out.append(('const', data[pos])); pos += 1
        elif t == 9:
            out.append(('const', struct.unpack_from('<H', data, pos)[0])); pos += 2
        else:
            break
    return out


@dataclass
class AvmFindings:
    external_calls: dict = field(default_factory=dict)    # name -> count ('{?}' marks a dynamic part)
    fscommands: dict = field(default_factory=dict)
    add_callbacks: dict = field(default_factory=dict)
    event_calls: dict = field(default_factory=dict)        # KeyMovieClip.EventCall(cmd) -> ExternalInterface.call(keyName, cmd, ...)
    members: set = field(default_factory=set)              # function names defined/assigned
    classes: set = field(default_factory=set)              # _global.<pkg>.<Class> = function
    string_members: dict = field(default_factory=dict)     # X.NAME = "literal"
    strings: set = field(default_factory=set)              # all constant/push strings
    actions: int = 0
    bytes: int = 0

    def resolved_external_calls(self) -> dict:
        """Resolve `Some.Class.CONST` call names through the string members."""
        out = {}
        for name, n in self.external_calls.items():
            if name.startswith('='):
                name = self.string_members.get(name[1:].split('.')[-1], name)
            out[name] = out.get(name, 0) + n
        return out


def scan_avm1(code: bytes, found: AvmFindings, pool=None, _depth=0):
    """Walk AVM1 bytecode with a tiny symbolic stack.  Precise enough to read
    `ExternalInterface.call(name, ...)` (literal, constant or `x + "literal"`
    names), `ExternalInterface.addCallback`, `fscommand`, AS2 class
    definitions and `x.name = function` assignments; whatever it does not
    understand resets the stack."""
    pool = list(pool or [])
    stack: list = []
    pos = 0
    found.bytes += len(code)

    def val(v):
        if isinstance(v, tuple) and v and v[0] == 'const':
            return pool[v[1]] if v[1] < len(pool) else None
        return v

    def pop():
        return stack.pop() if stack else None

    def name_of(v):
        if isinstance(v, str):
            return v
        if isinstance(v, _Ref) and v.path and v.path != '?' and not v.path.startswith('reg'):
            return '=' + v.path
        return None

    def count(bucket, key):
        bucket[key] = bucket.get(key, 0) + 1

    while pos < len(code):
        op = code[pos]
        pos += 1
        found.actions += 1
        if op == 0:
            break
        payload = b''
        if op >= 0x80:
            if pos + 2 > len(code):
                break
            length = struct.unpack_from('<H', code, pos)[0]
            payload = code[pos + 2:pos + 2 + length]
            pos += 2 + length
        if op == 0x88:          # ConstantPool
            n = struct.unpack_from('<H', payload, 0)[0]
            pool, p = [], 2
            for _ in range(n):
                s, p = cstring(payload, p)
                pool.append(s)
            found.strings.update(pool)
        elif op == 0x96:        # Push
            for v in _push_values(payload):
                v = val(v)
                if isinstance(v, str):
                    found.strings.add(v)
                stack.append(v)
        elif op == 0x1c:        # GetVariable
            name = pop()
            stack.append(_Ref(name if isinstance(name, str) else '?'))
        elif op == 0x4e:        # GetMember
            name, obj = pop(), pop()
            base = obj.path if isinstance(obj, _Ref) else '?'
            stack.append(_Ref(f'{base}.{name}' if isinstance(name, str) else '?'))
        elif op == 0x47:        # Add2: keep literal parts of string concatenation
            b, a = pop(), pop()
            if isinstance(a, str) and isinstance(b, str):
                stack.append(a + b)
            elif isinstance(a, str) or isinstance(b, str):
                stack.append((a if isinstance(a, str) else '{?}') + (b if isinstance(b, str) else '{?}'))
            else:
                stack.append(_Ref('?'))
        elif op == 0x52:        # CallMethod
            name, obj, n = pop(), pop(), pop()
            args = [pop() for _ in range(int(n))] if isinstance(n, (int, float)) and 0 <= n < 64 else []
            target = obj.path if isinstance(obj, _Ref) else ''
            if target.endswith('ExternalInterface') and args:
                key = name_of(args[0]) or '{?}'
                if name == 'call':
                    count(found.external_calls, key)
                elif name == 'addCallback':
                    count(found.add_callbacks, key)
            elif name == 'EventCall' and args:
                count(found.event_calls, name_of(args[0]) or '{?}')
            stack.append(_Ref('?'))
        elif op == 0x3d:        # CallFunction
            name, n = pop(), pop()
            args = [pop() for _ in range(int(n))] if isinstance(n, (int, float)) and 0 <= n < 64 else []
            if name == 'fscommand' and args:
                count(found.fscommands, name_of(args[0]) or '{?}')
            stack.append(_Ref('?'))
        elif op == 0x83:        # GetURL
            url, _ = cstring(payload, 0)
            if url.lower().startswith('fscommand:'):
                count(found.fscommands, url[10:])
        elif op == 0x9a:        # GetURL2
            _target, url = pop(), pop()
            if isinstance(url, str) and url.lower().startswith('fscommand:'):
                count(found.fscommands, url[10:] or '{?}')
        elif op in (0x9b, 0x8e):  # DefineFunction / DefineFunction2
            name, p = cstring(payload, 0)
            nparams = struct.unpack_from('<H', payload, p)[0]
            p += 2
            if op == 0x8e:
                p += 3
                for _ in range(nparams):
                    _, p = cstring(payload, p + 1)
            else:
                for _ in range(nparams):
                    _, p = cstring(payload, p)
            body_len = struct.unpack_from('<H', payload, p)[0]
            body = code[pos:pos + body_len]
            if _depth < 32:
                scan_avm1(body, found, pool, _depth + 1)
            pos += body_len
            if name:
                found.members.add(name)
            else:
                stack.append(_Func(name))
        elif op == 0x4f:        # SetMember
            value, name, obj = pop(), pop(), pop()
            if isinstance(name, str):
                if isinstance(value, _Func):
                    found.members.add(name)
                    path = obj.path if isinstance(obj, _Ref) else '?'
                    if path.startswith('_global.'):
                        path = path[8:]
                    # `pkg.sub.Class = function` (AS2 class definition); skip
                    # prototypes, registers, unknowns and timeline objects.
                    if path == '_global':
                        found.classes.add(name)
                    elif ('?' not in path and 'prototype' not in path and name[:1].isupper() and
                          not path.startswith(('reg', 'this', '_root', '_parent', '_level'))):
                        found.classes.add(path + '.' + name)
                elif isinstance(value, str):
                    found.string_members[name] = value
        elif op == 0x1d:        # SetVariable
            value, name = pop(), pop()
            if isinstance(value, _Func) and isinstance(name, str):
                found.members.add(name.split('.')[-1])
        elif op == 0x17:        # Pop
            pop()
        elif op == 0x4c:        # PushDuplicate
            if stack:
                stack.append(stack[-1])
        elif op == 0x87:        # StoreRegister keeps the value on the stack
            pass
        else:
            stack.clear()
    return found


def movie_avm1(movie: Movie) -> AvmFindings:
    found = AvmFindings()
    for t in movie_tags(movie):
        if t.code == 12:
            scan_avm1(t.data, found)
        elif t.code == 59 and len(t.data) > 2:
            scan_avm1(t.data[2:], found)
        elif t.code in (26, 70) and t.data and t.data[0] & 0x80:   # PlaceObject2/3 clip actions
            found.strings.add('<clip actions>')
    return found


# --------------------------------------------------------------------------- AVM2 (AS3) strings

def abc_strings(data: bytes) -> list:
    """Return the string constant pool of an ABC block (DoABC/DoABC2 payload)."""
    def u30(p):
        v, shift = 0, 0
        for _ in range(5):
            b = data[p]
            p += 1
            v |= (b & 0x7f) << shift
            shift += 7
            if not b & 0x80:
                break
        return v, p
    pos = 4  # minor, major
    n, pos = u30(pos)
    for _ in range(max(n - 1, 0)):
        _, pos = u30(pos)
    n, pos = u30(pos)
    for _ in range(max(n - 1, 0)):
        _, pos = u30(pos)
    n, pos = u30(pos)
    pos += 8 * max(n - 1, 0)
    n, pos = u30(pos)
    out = []
    for _ in range(max(n - 1, 0)):
        ln, pos = u30(pos)
        out.append(data[pos:pos + ln].decode('utf-8', errors='replace'))
        pos += ln
    return out


# --------------------------------------------------------------------------- DDS

@dataclass
class DdsInfo:
    width: int
    height: int
    mipmaps: int
    fourcc: str
    bits: int
    data_offset: int


def dds_info(data: bytes) -> DdsInfo:
    if data[:4] != b'DDS ' or len(data) < 128:
        raise FormatError('not a DDS image')
    (size, flags, height, width, pitch, depth, mips) = struct.unpack_from('<7I', data, 4)
    pf_flags = struct.unpack_from('<I', data, 80)[0]
    fourcc = data[84:88]
    bits = struct.unpack_from('<I', data, 88)[0]
    four = fourcc.decode('latin-1') if pf_flags & 4 else ('RGBA' if pf_flags & 0x41 == 0x41 else
                                                         'RGB' if pf_flags & 0x40 else
                                                         'L' if pf_flags & 0x20000 else f'pf{pf_flags:x}')
    return DdsInfo(width, height, max(mips, 1), four, bits, 128)


def _rgb565(c):
    r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


def _color_block(block: bytes, dxt1: bool):
    c0, c1, bits = struct.unpack_from('<HHI', block, 0)
    p0, p1 = _rgb565(c0), _rgb565(c1)
    if c0 > c1 or not dxt1:
        p2 = tuple((2 * a + b) // 3 for a, b in zip(p0, p1))
        p3 = tuple((a + 2 * b) // 3 for a, b in zip(p0, p1))
        pal = [p0 + (255,), p1 + (255,), p2 + (255,), p3 + (255,)]
    else:
        p2 = tuple((a + b) // 2 for a, b in zip(p0, p1))
        pal = [p0 + (255,), p1 + (255,), p2 + (255,), (0, 0, 0, 0)]
    return [pal[(bits >> (2 * i)) & 3] for i in range(16)]


def dds_decode_rgba(data: bytes) -> tuple[int, int, bytes]:
    """Decode the top mip level to straight RGBA8 (row-major, top row first)."""
    info = dds_info(data)
    w, h, p = info.width, info.height, info.data_offset
    out = bytearray(w * h * 4)
    if info.fourcc in ('DXT1', 'DXT3', 'DXT5'):
        bsize = 8 if info.fourcc == 'DXT1' else 16
        bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
        need = bw * bh * bsize
        if p + need > len(data):
            raise FormatError('DDS data truncated')
        for by in range(bh):
            for bx in range(bw):
                blk = data[p:p + bsize]
                p += bsize
                if info.fourcc == 'DXT1':
                    px = _color_block(blk, True)
                else:
                    px = _color_block(blk[8:], False)
                    if info.fourcc == 'DXT3':
                        a64 = int.from_bytes(blk[:8], 'little')
                        alphas = [((a64 >> (4 * i)) & 15) * 17 for i in range(16)]
                    else:
                        a0, a1 = blk[0], blk[1]
                        abits = int.from_bytes(blk[2:8], 'little')
                        if a0 > a1:
                            tab = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
                        else:
                            tab = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
                        alphas = [tab[(abits >> (3 * i)) & 7] for i in range(16)]
                    px = [c[:3] + (a,) for c, a in zip(px, alphas)]
                for i, c in enumerate(px):
                    x, y = bx * 4 + (i & 3), by * 4 + (i >> 2)
                    if x < w and y < h:
                        o = (y * w + x) * 4
                        out[o:o + 4] = bytes(c)
        return w, h, bytes(out)
    if info.fourcc in ('RGBA', 'RGB') and info.bits in (24, 32):
        rmask, gmask, bmask, amask = struct.unpack_from('<4I', data, 92)
        step = info.bits // 8
        need = w * h * step
        if p + need > len(data):
            raise FormatError('DDS data truncated')

        def shift(mask):
            return (mask & -mask).bit_length() - 1 if mask else 0
        shifts = [(m, shift(m)) for m in (rmask, gmask, bmask, amask)]
        for i in range(w * h):
            v = int.from_bytes(data[p + i * step:p + (i + 1) * step], 'little')
            px = [((v & m) >> s) if m else 255 for m, s in shifts]
            if info.fourcc == 'RGB':
                px[3] = 255
            out[i * 4:i * 4 + 4] = bytes(px)
        return w, h, bytes(out)
    raise FormatError(f'unsupported DDS pixel format {info.fourcc}/{info.bits}')
