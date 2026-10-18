#!/usr/bin/env python3
"""Inventory of the client's GFx interface files (NATIVE-GFX-001).

    gfx_inventory.py [--root MU_GAME_ROOT] [--json OUT.json] [--movie NAME ...] [--verbose]

Reads `Data/Interface/GFx` read-only and prints: the container layers, SWF
headers, tag counts (including GFx extension tags), ActionScript version,
AS2 classes (CLIK and the game's own), ExternalInterface/fscommand names,
fonts and font imports, external images and their DDS formats, and a cross
reference with the game-side boundary NATIVE-HUD-001 mapped.  The JSON report
contains names and counts from client files: keep it local.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gfxswf as g  # noqa: E402

# Game-side names from docs/research/client-hud.md (NATIVE-HUD-001).
HUD_CALLBACKS = [
    'onSkillTooltip', 'offSkillTooltip', 'onItemTooltip', 'offItemTooltip', 'onExpTooltip', 'useItemHotKey',
    'registItemHotKey', 'onHotKey', 'onOpenSkillWindow', 'onSelectSkill', 'onLoadSkillSlot', 'onLoad',
    'requestSlotInfo', 'requestItemSlotClick', 'requestItemSlotDoubleClick', 'requestItemSlotClickR',
    'requestItemSlotOver', 'requestItemSlotOut', 'onCloseBtnClick', 'OnHotkeyExpand', 'onClickbtnMasterSkillTree',
    'OnClick4thSkillTree', 'OnClick5thSkillTree',
]
HUD_INVOKES = [
    'setHPMP', 'mcItemHotKey', 'mcSkillHotKey', 'mcExpBar', 'setRideInfo', 'SetZenText', 'SetRuudText', 'InitText',
    'SetRageFighter', 'SetMagicGladiator', 'SetGhostKnight', 'SocketOptionEnabled', 'SetOptionEnabled',
    'SetElementalText', 'SetCharacterName', 'SetVisible', 'SetInfoPopup', 'SetInfoPopupCompareItem',
    'SetInfoPopupEx', 'SetInfoPopupDirection', 'CloseInfoPopup',
]


# Scaleform GFx ActionScript 2 extensions (Scaleform "GFx extensions" API
# names; none of them exist in the Flash Player or in Ruffle).
GFX_AS_EXTENSIONS = [
    'gfxExtensions', 'gfxVersion', 'hitTestDisable', 'noAdvance', 'topmostLevel', 'focusGroupMask',
    'onPressAux', 'onReleaseAux', 'onReleaseOutsideAux', 'onRollOverAux', 'onRollOutAux', 'onDragOverAux',
    'onDragOutAux', 'textAutoSize', 'verticalAlign', 'verticalAutoSize', 'fontScaleFactor', 'getExactCharBoundaries',
    'appendHtml', 'noTranslate', 'shadowStyle', 'shadowColor', 'captureFocus', 'disableFocusAutoRelease',
    'disableFocusKeys', 'disableFocusRolloverEvent', 'alwaysEnableArrowKeys', 'alwaysEnableKeyboardPress',
    'modalClip', 'setModalClip', 'moveFocus', 'findFocus', 'getFocusBitmask', 'setControllerFocusGroup',
    'setCursorType', 'getButtonsState', 'getTopMostEntity', 'visibleRect', 'safeRect', 'originalRect',
    'loadBitmapFromLib', 'imeEnabled', 'useRichTextClipboard', 'inactiveSelectionBkgColor', 'selectionBkgColor',
]


def default_root() -> Path | None:
    root = os.environ.get('MU_GAME_ROOT')
    return Path(root) if root else None


def movie_record(path: Path, gfx_dir: Path) -> dict:
    rec: dict = {'file': path.relative_to(gfx_dir).as_posix(), 'bytes': path.stat().st_size}
    try:
        layer, data = g.read_container(path)
        movie = g.parse_movie(data)
    except (g.FormatError, OSError, ValueError, struct.error) as exc:
        rec['error'] = str(exc)
        return rec
    rec.update(layer=layer, signature=movie.signature, swf_version=movie.version,
               uncompressed=len(movie.body) + 8, stage=[movie.width, movie.height],
               frame_rate=movie.frame_rate, frames=movie.frame_count)
    top, nested = collections.Counter(), collections.Counter()
    images, fonts, imports, texts = [], [], [], {'count': 0, 'html': 0, 'device_font': 0, 'font_class': 0}
    sub_images, exporter, as3 = 0, None, False
    for t in g.movie_tags(movie):
        (nested if t.depth else top)[t.name] += 1
        if t.code == 1000:
            exporter = g.parse_exporter_info(t.data)
        elif t.code in (1001, 1009):
            info = g.parse_external_image(t)
            src = gfx_dir/f'{Path(info["file"]).stem}.ozd'
            info['ozd'] = src.exists()
            if src.exists():
                try:
                    dds = g.dds_info(g.read_container(src)[1])
                    info['dds'] = [dds.fourcc, dds.width, dds.height, dds.mipmaps]
                except (g.FormatError, OSError) as exc:
                    info['dds_error'] = str(exc)
            info['atlas'] = bool(info['id'] >> 16)
            images.append(info)
        elif t.code == 1008:
            sub_images += 1
        elif t.code in (48, 75):
            fonts.append(g.parse_font(t))
        elif t.code == 1005:
            fonts.append(g.parse_compacted_font(t))
        elif t.code in (57, 71):
            imports.append(g.parse_import_assets(t))
        elif t.code == 37:
            et = g.parse_edit_text(t)
            texts['count'] += 1
            texts['html'] += et['html']
            texts['device_font'] += 'font' not in et and 'font_class' not in et
            texts['font_class'] += 'font_class' in et
        elif t.code == 69:
            as3 = bool(t.data[0] & 0x08)
        elif t.code in (72, 82):
            as3 = True
    avm = g.movie_avm1(movie)
    rec.update(tags=dict(top.most_common()), sprite_tags=dict(nested.most_common()), exporter=exporter,
               external_images=images, sub_images=sub_images, fonts=fonts, imports=imports, edit_texts=texts,
               actionscript='AS3' if as3 else ('AS2' if top['DoAction'] + top['DoInitAction'] + nested['DoAction']
                                                else 'none'),
               avm1_bytes=avm.bytes,
               classes=sorted(avm.classes),
               clik_classes=sorted(c for c in avm.classes if c.startswith('gfx.')),
               external_calls=avm.resolved_external_calls(), event_calls=avm.event_calls,
               add_callbacks=avm.add_callbacks, fscommands=avm.fscommands,
               members=sorted(avm.members),
               hud_names=sorted(n for n in set(HUD_CALLBACKS + HUD_INVOKES)
                                if n in avm.strings or n in avm.members),
               gfx_extensions=sorted(n for n in GFX_AS_EXTENSIONS if n in avm.strings or n in avm.members))
    return rec


def image_summary(gfx_dir: Path) -> dict:
    formats = collections.Counter()
    sizes = collections.Counter()
    errors = []
    for p in sorted(gfx_dir.glob('*.ozd')):
        try:
            info = g.dds_info(g.read_container(p)[1])
            formats[f'{info.fourcc}{"/" + str(info.bits) if info.bits else ""}'] += 1
            sizes[f'{info.width}x{info.height}'] += 1
        except (g.FormatError, OSError) as exc:
            errors.append([p.name, str(exc)])
    return {'formats': dict(formats.most_common()), 'sizes': dict(sizes.most_common(12)), 'errors': errors}


def build(root: Path, only: list | None = None) -> dict:
    gfx_dir = root/'Data/Interface/GFx'
    if not gfx_dir.is_dir():
        raise SystemExit(f'{gfx_dir} not found')
    files = [p for p in gfx_dir.rglob('*') if p.is_file()]
    ext = collections.Counter(p.suffix.lower() or '(none)' for p in files)
    movies = sorted(p for p in files if p.suffix.lower() in ('.ozg', '.swf', '.gfx'))
    if only:
        movies = [p for p in movies if p.stem in only]
    records = [movie_record(p, gfx_dir) for p in movies]
    report = {'gfx_dir': str(gfx_dir), 'extensions': dict(ext.most_common()), 'movies': records}
    if not only:
        report['ozd'] = image_summary(gfx_dir)
    return report


def aggregate(report: dict) -> dict:
    ok = [m for m in report['movies'] if 'error' not in m and m['file'].endswith('.ozg')]
    agg: dict = {'ozg_movies': len(ok), 'errors': [[m['file'], m['error']] for m in report['movies'] if 'error' in m]}
    for key in ('signature', 'swf_version', 'actionscript', 'layer'):
        agg[key] = dict(collections.Counter(str(m[key]) for m in ok))
    agg['exporter'] = dict(collections.Counter(m['exporter']['version'] if m['exporter'] else 'none' for m in ok))
    tags = collections.Counter()
    for m in ok:
        tags.update(m['tags'])
        tags.update(m['sprite_tags'])
    agg['tags'] = dict(tags.most_common())
    agg['external_images'] = sum(len(m['external_images']) for m in ok)
    agg['atlases'] = sum(i['atlas'] for m in ok for i in m['external_images'])
    agg['missing_images'] = [[m['file'], i['file']] for m in ok for i in m['external_images'] if not i['ozd']]
    agg['sub_images'] = sum(m['sub_images'] for m in ok)
    agg['imports'] = dict(collections.Counter(f'{i["url"]}:{a[1]}' for m in ok for i in m['imports']
                                              for a in i['assets']))
    agg['embedded_fonts'] = dict(collections.Counter(f'{f["kind"]}:{f["name"]}' for m in ok for f in m['fonts']))
    agg['edit_texts'] = {k: sum(m['edit_texts'][k] for m in ok) for k in ('count', 'html', 'device_font')}
    clik = collections.Counter(c for m in ok for c in m['clik_classes'])
    agg['clik_classes'] = dict(clik.most_common())
    own = collections.Counter(c for m in ok for c in m['classes'] if not c.startswith(('gfx.', 'mx.', 'caurina.')))
    agg['game_classes'] = len(own)
    calls = collections.Counter()
    for m in ok:
        calls.update(m['external_calls'])
    agg['external_calls'] = dict(calls.most_common())
    events = collections.Counter()
    for m in ok:
        events.update(m['event_calls'])
    agg['event_calls'] = dict(events.most_common())
    agg['gfx_extensions'] = dict(collections.Counter(n for m in ok for n in m['gfx_extensions']).most_common())
    agg['fscommands'] = dict(collections.Counter(k for m in ok for k in m['fscommands']))
    agg['add_callbacks'] = dict(collections.Counter(k for m in ok for k in m['add_callbacks']))
    xref = {}
    for name in HUD_CALLBACKS + HUD_INVOKES:
        xref[name] = sorted(Path(m['file']).stem for m in ok if name in m['hud_names'])
    agg['hud_xref'] = xref
    return agg


def print_report(report: dict, agg: dict, verbose: bool):
    print(f'GFx directory: {report["gfx_dir"]}')
    print('files by extension:', ', '.join(f'{k} {v}' for k, v in report['extensions'].items()))
    print(f'movies (.ozg) parsed: {agg["ozg_movies"]}; errors: {len(agg["errors"])}')
    for k in ('layer', 'signature', 'swf_version', 'actionscript', 'exporter'):
        print(f'  {k}: {agg[k]}')
    print('tag inventory (top level + sprites):')
    for name, n in agg['tags'].items():
        print(f'  {n:7d} {name}')
    print(f'external images: {agg["external_images"]} ({agg["atlases"]} atlases), sub-images: {agg["sub_images"]},'
          f' missing .ozd: {len(agg["missing_images"])}')
    if 'ozd' in report:
        print('  .ozd DDS formats:', report['ozd']['formats'])
        print('  .ozd common sizes:', report['ozd']['sizes'])
    print('font imports:', agg['imports'])
    print('embedded fonts:', agg['embedded_fonts'])
    print('edit texts:', agg['edit_texts'])
    print(f'CLIK classes used ({len(agg["clik_classes"])}):', ', '.join(agg['clik_classes']))
    print(f'game AS2 classes (distinct): {agg["game_classes"]}')
    print(f'ExternalInterface.call names ({len(agg["external_calls"])}):')
    for name, n in agg['external_calls'].items():
        print(f'  {n:5d} {name}')
    print(f'EventCall commands ({len(agg["event_calls"])}):', ', '.join(agg['event_calls']))
    print('GFx AS2 extensions (movies using each):', agg['gfx_extensions'])
    print('fscommand:', agg['fscommands'] or 'none', '; addCallback:', agg['add_callbacks'] or 'none')
    print('NATIVE-HUD-001 names found in movies:')
    for name, where in agg['hud_xref'].items():
        print(f'  {name:28s} {", ".join(where[:8]) + (" ..." if len(where) > 8 else "") if where else "-"}')
    if verbose:
        for m in report['movies']:
            if 'error' in m:
                print(f'{m["file"]}: ERROR {m["error"]}')
                continue
            print(f'{m["file"]}: {m["signature"]}{m["swf_version"]} {m["stage"][0]:.0f}x{m["stage"][1]:.0f} '
                  f'{m["frame_rate"]}fps {m["actionscript"]} imgs={len(m["external_images"])} '
                  f'sub={m["sub_images"]} texts={m["edit_texts"]["count"]} calls={len(m["external_calls"])}')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', type=Path, default=default_root())
    ap.add_argument('--json', type=Path, help='write the full report (keep it local)')
    ap.add_argument('--movie', action='append', help='only these movie stems')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args(argv)
    if not args.root:
        ap.error('--root or MU_GAME_ROOT is required')
    report = build(args.root, args.movie)
    agg = aggregate(report)
    report['aggregate'] = agg
    print_report(report, agg, args.verbose)
    if args.json:
        args.json.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=list))
    return 0


if __name__ == '__main__':
    sys.exit(main())
