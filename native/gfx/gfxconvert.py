"""Turn a client GFx movie into a standard SWF that a stock Flash player
(Ruffle) can load (NATIVE-GFX-001).

What GFx adds and what this converter does with it:

* `CFX`/`GFX` header -> `CWS`/`FWS` (same zlib body).
* `ExporterInfo` (1000): dropped (exporter metadata and AS code offsets).
* `DefineExternalImage2` (1009) / `DefineExternalImage` (1001): the image lives
  in `<name>.ozd` (ModulusCrypt envelope around DDS).  Ids below 0x10000 are
  ordinary bitmap characters: the DDS (often stretched to a power of two) is
  decoded, resampled to the declared target size and written as a
  `DefineBitsLossless2`.  Ids 0x9xxxx are texture atlases, kept in memory only.
* `DefineSubImage` (1008): a rectangle of an atlas (low 16 bits of the atlas
  id) bound to a character id -> cropped `DefineBitsLossless2`.
* `ImportAssets2` from `gfxfontlib.swf`: the GFx font library.  The imported
  font is copied in (renamed to its `$Symbol` name, as GFx's font map resolves
  it), so the movie needs no import at run time.
* `DefineCompactedFont` (1005, GFx's packed font format; six movies, all the
  font "Slate Mobile"): replaced by the DefineFont2/3 of the same name that
  other movies of the same GFx directory carry (NATIVE-GFX-002), with the
  compacted font's character id, so the movie's text fields keep their font.
  The packed glyph data itself is not decoded.  Without such a font the
  fontconfig `$NormalFont` font is used under that name.
* External sounds/gradients: reported, not converted.
* NATIVE-MAP-001: the world images of hudMap (`NaviMap/Navimap<NN>.OZP`, a PNG
  behind a 4-byte copy of the PNG signature) are written as plain PNG files
  under `<out>/NaviMap/` with the name the movie asks for (`navimap<NN>.ozp`).

The conversion is a local preprocessing step; its outputs contain client data
and must stay out of the repository.
"""
from __future__ import annotations

import io
import re
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import gfxswf as g

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow is in the portable requirements
    Image = None


@dataclass
class Report:
    images: int = 0
    sub_images: int = 0
    atlases: int = 0
    fonts_inlined: list = field(default_factory=list)
    missing_files: list = field(default_factory=list)
    unconverted: dict = field(default_factory=dict)
    dropped: dict = field(default_factory=dict)

    def note(self, bucket: dict, name: str):
        bucket[name] = bucket.get(name, 0) + 1


# --------------------------------------------------------------------------- images

def decode_dds(data: bytes):
    """RGBA image (Pillow) of the top mip level."""
    if Image is not None:
        try:
            return Image.open(io.BytesIO(data)).convert('RGBA')
        except Exception:
            pass
    w, h, px = g.dds_decode_rgba(data)
    if Image is None:
        raise g.FormatError('Pillow is required for image conversion')
    return Image.frombytes('RGBA', (w, h), px)


def lossless2(cid: int, image) -> bytes:
    """DefineBitsLossless2 payload: premultiplied ARGB, zlib."""
    from PIL import ImageChops
    image = image.convert('RGBA')
    w, h = image.size
    r, gg, b, a = image.split()
    argb = Image.merge('RGBA', (a, ImageChops.multiply(r, a), ImageChops.multiply(gg, a),
                                ImageChops.multiply(b, a))).tobytes()
    return struct.pack('<HBHH', cid, 5, w, h) + zlib.compress(argb, 6)


def ozd_path(movie_dir: Path, file_name: str) -> Path:
    stem = Path(file_name.replace('\\', '/')).stem
    return movie_dir/f'{stem}.ozd'


# --------------------------------------------------------------------------- fonts

def font_tags_by_export(lib_movie: g.Movie) -> dict:
    """export name -> list of tags (font + align zones + name) of a font library."""
    by_id: dict = {}
    exports = {}
    for t in g.movie_tags(lib_movie):
        if t.depth:
            continue
        if t.code in (10, 48, 75, 91):
            by_id.setdefault(g.define_id(t), []).insert(0, t)
        elif t.code in (73, 88):
            by_id.setdefault(struct.unpack_from('<H', t.data, 0)[0], []).append(t)
        elif t.code == 56:
            for cid, name in g.parse_assets(t):
                exports[name] = cid
    return {name: by_id.get(cid, []) for name, cid in exports.items()}


def font_tags_by_name(lib_movie: g.Movie) -> dict:
    by_id: dict = {}
    names = {}
    for t in g.movie_tags(lib_movie):
        if t.depth:
            continue
        if t.code in (48, 75):
            fid = g.define_id(t)
            by_id.setdefault(fid, []).insert(0, t)
            info = g.parse_font(t)
            names[(info['name'], info['bold'])] = fid
        elif t.code in (73, 88):
            by_id.setdefault(struct.unpack_from('<H', t.data, 0)[0], []).append(t)
    return {key: by_id[fid] for key, fid in names.items()}


def parse_fontconfig(text: str) -> dict:
    """fontconfig.txt -> {config name: {'fontlib': [...], 'map': {sym: (font, style)}}}."""
    configs, cur = {}, None
    for line in text.splitlines():
        line = line.strip().lstrip('﻿')
        m = re.match(r'\[FontConfig "([^"]+)"\]', line)
        if m:
            cur = configs.setdefault(m.group(1), {'fontlib': [], 'map': {}})
            continue
        if cur is None:
            continue
        m = re.match(r'fontlib "([^"]+)"', line)
        if m:
            cur['fontlib'].append(m.group(1))
        m = re.match(r'map "([^"]+)" = "([^"]+)"\s*(\w+)?', line)
        if m:
            cur['map'][m.group(1)] = (m.group(2), (m.group(3) or 'Normal'))
    return configs


def rename_font(tag: g.Tag, new_id: int, new_name: str | None) -> bytes:
    d = tag.data
    if tag.code in (48, 75) and new_name is not None:
        enc = new_name.encode('utf-8')
        old_len = d[4]
        return struct.pack('<H', new_id) + d[2:4] + bytes([len(enc)]) + enc + d[5 + old_len:]
    return struct.pack('<H', new_id) + d[2:]


LATIN_SUBSET = ((0x20, 0x24f), (0x2000, 0x22ff), (0x2460, 0x27bf), (0xff00, 0xffef))


def subset_font3(data: bytes, keep) -> bytes:
    """DefineFont3 payload restricted to the code points accepted by keep(cp).
    Glyph shapes are copied byte for byte; offsets are rewritten (wide), the
    layout tables (advance, bounds, kerning) are filtered alongside."""
    fid, flags, lang, nlen = struct.unpack_from('<HBBB', data, 0)
    pos = 5 + nlen
    name = data[5:pos]
    n = struct.unpack_from('<H', data, pos)[0]
    pos += 2
    wide_off, wide_codes, layout = flags & 0x08, flags & 0x04, flags & 0x80
    if not wide_codes:
        return data
    osz = 4 if wide_off else 2
    table = pos
    offsets = [struct.unpack_from('<I' if wide_off else '<H', data, table + i * osz)[0] for i in range(n)]
    code_off = struct.unpack_from('<I' if wide_off else '<H', data, table + n * osz)[0]
    shapes = [data[table + offsets[i]:table + (offsets[i + 1] if i + 1 < n else code_off)] for i in range(n)]
    cpos = table + code_off
    codes = list(struct.unpack_from(f'<{n}H', data, cpos))
    pos = cpos + 2 * n
    tail = b''
    advances = bounds = kerning = None
    if layout:
        metrics = data[pos:pos + 6]
        pos += 6
        advances = list(struct.unpack_from(f'<{n}h', data, pos))
        pos += 2 * n
        bounds = []
        for _ in range(n):
            start = pos
            _, pos = g.read_rect(data, pos)
            bounds.append(data[start:pos])
        kcount = struct.unpack_from('<H', data, pos)[0]
        pos += 2
        kerning = [struct.unpack_from('<HHh', data, pos + 6 * i) for i in range(kcount)]
        tail = metrics
    kept = [i for i in range(n) if keep(codes[i])]
    keep_codes = {codes[i] for i in kept}
    out = bytearray(struct.pack('<HBBB', fid, flags | 0x08, lang, nlen) + name + struct.pack('<H', len(kept)))
    base = 4 * len(kept) + 4
    offs, cur = [], base
    for i in kept:
        offs.append(cur)
        cur += len(shapes[i])
    out += b''.join(struct.pack('<I', o) for o in offs) + struct.pack('<I', cur)
    out += b''.join(shapes[i] for i in kept)
    out += b''.join(struct.pack('<H', codes[i]) for i in kept)
    if layout:
        out += tail
        out += b''.join(struct.pack('<h', advances[i]) for i in kept)
        out += b''.join(bounds[i] for i in kept)
        ks = [k for k in kerning if k[0] in keep_codes and k[1] in keep_codes]
        out += struct.pack('<H', len(ks)) + b''.join(struct.pack('<HHh', *k) for k in ks)
    return bytes(out)


class FontResolver:
    """Resolves GFx font imports (`$NormalFont` ...) to font tags."""

    def __init__(self, movie_dir: Path, config: str | None = None, subset=None):
        self.movie_dir = Path(movie_dir)
        self.config = config
        self.subset = subset      # None or ((lo, hi), ...) code point ranges
        self._libs: dict = {}
        self.mapping = {}
        if config:
            cfg = parse_fontconfig((self.movie_dir/'fontconfig.txt').read_text(encoding='utf-8-sig'))
            if config not in cfg:
                raise g.FormatError(f'font config {config!r} not in fontconfig.txt ({", ".join(cfg)})')
            self.mapping = cfg[config]

    def _lib(self, rel: str) -> g.Movie:
        if rel not in self._libs:
            _, data = g.read_container(self.movie_dir/rel)
            self._libs[rel] = g.parse_movie(data)
        return self._libs[rel]

    def font_by_name(self, name: str):
        """-> (tags, source) of the glyph-richest DefineFont2/3 called `name`
        in the GFx directory's movies (cached), or (None, reason)."""
        if not hasattr(self, '_named'):
            self._named = {}
        if name in self._named:
            return self._named[name]
        best = (None, f'no movie defines {name!r} with glyphs')
        best_glyphs = 0
        for path in sorted(self.movie_dir.glob('*.ozg')):
            try:
                movie = g.parse_movie(g.read_container(path)[1])
            except (g.FormatError, OSError, ValueError):
                continue
            fonts = font_tags_by_name(movie)
            for (fname, _bold), tags in fonts.items():
                if fname != name:
                    continue
                info = g.parse_font(tags[0])
                if info['glyphs'] > best_glyphs:
                    best, best_glyphs = (tags, f'{path.stem}:{fname} ({info["glyphs"]} glyphs)'), info['glyphs']
        self._named[name] = best
        return best

    def resolve(self, url: str, symbol: str):
        """-> (tags, source description) or (None, reason)."""
        if self.mapping and symbol in self.mapping['map']:
            name, style = self.mapping['map'][symbol]
            for rel in self.mapping['fontlib']:
                fonts = font_tags_by_name(self._lib(rel))
                tags = fonts.get((name, style == 'Bold')) or fonts.get((name, False)) or fonts.get((name, True))
                if tags:
                    return tags, f'{rel}:{name}'
        path = self.movie_dir/url
        if not path.exists():
            return None, f'{url} missing'
        tags = font_tags_by_export(self._lib(url)).get(symbol)
        if not tags:
            return None, f'{symbol} not exported by {url}'
        return tags, f'{url}:{symbol}'


# --------------------------------------------------------------------------- convert

def convert_movie(path: Path, fonts: FontResolver | None = None, drop_background: bool = False,
                  compress: bool = True, bridge: bool = False,
                  init_vars: dict | None = None) -> tuple[bytes, Report]:
    path = Path(path)
    movie_dir = path.parent
    fonts = fonts or FontResolver(movie_dir)
    _, data = g.read_container(path)
    movie = g.parse_movie(data)
    report = Report()
    atlases: dict = {}       # atlas index -> (image, (target w, h))
    out = bytearray()
    header = movie.body[:movie.tags_offset]

    pos = movie.tags_offset
    body = movie.body
    # Top-level walk (sprites are copied unchanged; GFx extension tags were
    # observed only at the top level).
    while pos < len(body):
        hdr = struct.unpack_from('<H', body, pos)[0]
        start = pos
        pos += 2
        code, length = hdr >> 6, hdr & 0x3f
        if length == 0x3f:
            length = struct.unpack_from('<I', body, pos)[0]
            pos += 4
        payload = body[pos:pos + length]
        pos += length
        tag = g.Tag(code, payload)
        if code == 1000:
            report.note(report.dropped, tag.name)
            continue
        if code == 9 and drop_background:
            report.note(report.dropped, tag.name)
            continue
        if code in (1001, 1009):
            info = g.parse_external_image(tag)
            src = ozd_path(movie_dir, info['file'])
            if not src.exists():
                report.missing_files.append(info['file'])
                continue
            img = decode_dds(g.read_container(src)[1])
            if info['id'] >> 16:
                atlases[info['id'] & 0xffff] = (img, (info['width'], info['height']))
                report.atlases += 1
                continue
            if img.size != (info['width'], info['height']) and info['width'] and info['height']:
                img = img.resize((info['width'], info['height']), Image.BILINEAR)
            out += g.encode_tag(36, lossless2(info['id'], img))
            report.images += 1
            continue
        if code == 1008:
            info = g.parse_sub_image(tag)
            if info['image'] not in atlases:
                report.note(report.unconverted, 'DefineSubImage without atlas')
                continue
            img, (tw, th) = atlases[info['image']]
            x1, y1, x2, y2 = info['rect']
            if img.size != (tw, th) and tw and th:
                sx, sy = img.size[0] / tw, img.size[1] / th
                crop = img.crop((round(x1 * sx), round(y1 * sy), round(x2 * sx), round(y2 * sy)))
                crop = crop.resize((max(x2 - x1, 1), max(y2 - y1, 1)), Image.BILINEAR)
            else:
                crop = img.crop((x1, y1, x2, y2))
            out += g.encode_tag(36, lossless2(info['id'], crop))
            report.sub_images += 1
            continue
        if code in (57, 71):
            imp = g.parse_import_assets(tag)
            kept = []
            for cid, symbol in imp['assets']:
                tags, source = fonts.resolve(imp['url'], symbol)
                if not tags:
                    kept.append((cid, symbol))
                    report.note(report.unconverted, f'import {imp["url"]}:{symbol} ({source})')
                    continue
                for ft in tags:
                    if fonts.subset and ft.code == 73:
                        continue      # alignment zones are per glyph; dropped with a subset
                    if fonts.subset and ft.code == 75:
                        ranges = fonts.subset
                        ft = g.Tag(75, subset_font3(ft.data, lambda c: any(lo <= c <= hi for lo, hi in ranges)))
                    out += g.encode_tag(ft.code, rename_font(ft, cid, symbol if ft.code in (48, 75) else None),
                                        force_long=True)
                report.fonts_inlined.append(f'{symbol}<-{source}')
            if kept:
                out += body[start:pos]
            continue
        if code == 1005:
            info = g.parse_compacted_font(tag)
            tags, source = fonts.font_by_name(info['name']) if info['name'] else (None, 'unnamed')
            if not tags:
                tags, source = fonts.resolve('gfxfontlib.swf', '$NormalFont')
            if not tags:
                report.note(report.unconverted, f'{tag.name} {info["name"]} ({source})')
                continue
            for ft in tags:
                out += g.encode_tag(ft.code, rename_font(ft, info['id'], info['name'] if ft.code in (48, 75) else None),
                                    force_long=True)
            report.fonts_inlined.append(f'{info["name"]}(compacted)<-{source}')
            continue
        if code in (1002, 1003, 1004, 1006, 1007):
            report.note(report.unconverted, tag.name)
            continue
        out += body[start:pos]
    tags = bytes(out)
    if bridge or init_vars:
        actions = bridge_actions(init_vars) if bridge else _init_only(init_vars)
        tags = insert_before_first_show_frame(tags, g.encode_tag(12, actions))
    return g.write_swf(movie.version, header, tags, compress), report


def _init_only(init_vars: dict) -> bytes:
    code = b''.join(_push(k, v) + SET_VARIABLE for k, v in init_vars.items())
    return code + b'\0'


# --------------------------------------------------------------------------- host bridge

def _push(*values) -> bytes:
    out = bytearray()
    for v in values:
        if v is None:
            out += b'\x02'
        elif isinstance(v, bool):
            out += b'\x05' + bytes([int(v)])
        elif isinstance(v, int):
            out += b'\x07' + struct.pack('<i', v)
        else:
            out += b'\x00' + v.encode('utf-8') + b'\0'
    return b'\x96' + struct.pack('<H', len(out)) + bytes(out)


def _function(params: list, body: bytes) -> bytes:
    """DefineFunction (v1) without a name: pushes the function object."""
    p = b'\0' + struct.pack('<H', len(params)) + b''.join(x.encode() + b'\0' for x in params)
    p += struct.pack('<H', len(body))
    return b'\x9b' + struct.pack('<H', len(p)) + p + body


GET_VARIABLE, GET_MEMBER, SET_VARIABLE, CALL_METHOD, POP, RETURN, DEFINE_LOCAL = (
    b'\x1c', b'\x4e', b'\x1d', b'\x52', b'\x17', b'\x3e', b'\x3c')

BRIDGE_CALLBACKS = ('__mu_invoke', '__mu_set', '__mu_get')


def _ei_add_callback(name: str, fn: bytes) -> bytes:
    """flash.external.ExternalInterface.addCallback(name, null, fn);"""
    return (fn + _push(None, name, 3, 'flash') + GET_VARIABLE + _push('external') + GET_MEMBER +
            _push('ExternalInterface') + GET_MEMBER + _push('addCallback') + CALL_METHOD + POP)


def bridge_actions(init_vars: dict | None = None) -> bytes:
    """AVM1 code that exposes GFx-style host access through ExternalInterface:

    * __mu_invoke(path, method, args): `eval(path)[method].apply(eval(path), args)`
      (GFx `Movie::Invoke` / `Value::Invoke` on a display-object path);
    * __mu_set(path, value): `set(path, value)` (GFx `SetVariable`);
    * __mu_get(path): `eval(path)` (GFx `GetVariable`).

    `init_vars` are assigned first (e.g. `_root.isClient = true`, which the
    client sets before the first advance)."""
    code = bytearray()
    for path, value in (init_vars or {}).items():
        code += _push(path, value) + SET_VARIABLE
    # apply(thisArg, args): push args (arg 2), thisArg (arg 1), count, function, "apply".
    invoke = (_push('o', 'path') + GET_VARIABLE + GET_VARIABLE + DEFINE_LOCAL +
              _push('args') + GET_VARIABLE + _push('o') + GET_VARIABLE + _push(2) +
              _push('o') + GET_VARIABLE + _push('method') + GET_VARIABLE + GET_MEMBER +
              _push('apply') + CALL_METHOD + RETURN)
    setter = _push('path') + GET_VARIABLE + _push('value') + GET_VARIABLE + SET_VARIABLE
    getter = _push('path') + GET_VARIABLE + GET_VARIABLE + RETURN
    code += _ei_add_callback('__mu_invoke', _function(['path', 'method', 'args'], invoke))
    code += _ei_add_callback('__mu_set', _function(['path', 'value'], setter))
    code += _ei_add_callback('__mu_get', _function(['path'], getter))
    return bytes(code) + b'\0'


def insert_before_first_show_frame(swf_tags: bytes, action_tag: bytes) -> bytes:
    pos = 0
    while pos < len(swf_tags):
        hdr = struct.unpack_from('<H', swf_tags, pos)[0]
        code, length = hdr >> 6, hdr & 0x3f
        head = 2
        if length == 0x3f:
            length = struct.unpack_from('<I', swf_tags, pos + 2)[0]
            head = 6
        if code == 1:
            return swf_tags[:pos] + action_tag + swf_tags[pos:]
        pos += head + length
    return swf_tags + action_tag


# --------------------------------------------------------------------------- CLI

def _parse_var(text: str):
    key, _, value = text.partition('=')
    if value in ('true', 'false'):
        return key, value == 'true'
    try:
        return key, int(value)
    except ValueError:
        return key, value


def convert_navimaps(gfx_dir: Path, out: Path) -> int:
    """NaviMap/*.OZP -> out/NaviMap/<lower-case name>: the PNG after the 4-byte prefix (NATIVE-MAP-001)."""
    src = gfx_dir/'NaviMap'
    if not src.is_dir():
        return 0
    n = 0
    (out/'NaviMap').mkdir(parents=True, exist_ok=True)
    for f in sorted(src.iterdir()):
        if f.suffix.lower() != '.ozp':
            continue
        data = f.read_bytes()
        png = data[4:] if data[4:12] == b'\x89PNG\r\n\x1a\n' else data
        (out/'NaviMap'/f.name.lower()).write_bytes(png)
        n += 1
    return n


def main(argv=None):
    import argparse
    import json
    import os
    import sys
    import time
    ap = argparse.ArgumentParser(description='Convert client GFx movies (.ozg) to standard SWF files (local only).')
    ap.add_argument('--root', type=Path, default=Path(os.environ['MU_GAME_ROOT']) if os.environ.get('MU_GAME_ROOT')
                    else None)
    ap.add_argument('--out', type=Path, required=True, help='output directory (outside the repository)')
    ap.add_argument('--movie', action='append', help='movie stem (default: all .ozg)')
    ap.add_argument('--fontconfig', help='resolve $Font imports through fontconfig.txt (e.g. English)')
    ap.add_argument('--font-subset', choices=['latin'], help='keep only these code points of inlined fonts')
    ap.add_argument('--bridge', action='store_true', help='add the __mu_invoke/__mu_set/__mu_get host bridge')
    ap.add_argument('--var', action='append', default=[], help='PATH=VALUE set before the first frame')
    ap.add_argument('--transparent', action='store_true', help='drop SetBackgroundColor')
    ap.add_argument('--report', type=Path, help='write a JSON conversion report')
    args = ap.parse_args(argv)
    if not args.root:
        ap.error('--root or MU_GAME_ROOT is required')
    gfx_dir = args.root/'Data/Interface/GFx'
    args.out.mkdir(parents=True, exist_ok=True)
    stems = args.movie or sorted(p.stem for p in gfx_dir.glob('*.ozg'))
    fonts = FontResolver(gfx_dir, args.fontconfig, LATIN_SUBSET if args.font_subset == 'latin' else None)
    init_vars = dict(_parse_var(v) for v in args.var) or None
    results = {}
    for stem in stems:
        t0 = time.time()
        try:
            swf, rep = convert_movie(gfx_dir/f'{stem}.ozg', fonts, args.transparent, True, args.bridge, init_vars)
        except (g.FormatError, OSError, ValueError, struct.error) as exc:
            results[stem] = {'error': str(exc)}
            print(f'{stem}: ERROR {exc}', file=sys.stderr)
            continue
        (args.out/f'{stem}.swf').write_bytes(swf)
        results[stem] = {'bytes': len(swf), 'seconds': round(time.time() - t0, 3), **rep.__dict__}
        print(f'{stem}: {len(swf)} bytes, {rep.images} images, {rep.sub_images} sub-images, '
              f'{rep.atlases} atlases, fonts {rep.fonts_inlined}, missing {rep.missing_files}, '
              f'unconverted {rep.unconverted}')
    if not args.movie:
        results['NaviMap'] = {'images': convert_navimaps(gfx_dir, args.out)}
    if args.report:
        args.report.write_text(json.dumps(results, indent=1, ensure_ascii=False))
    return 1 if any('error' in r for r in results.values()) else 0


if __name__ == '__main__':
    raise SystemExit(main())
