#!/usr/bin/env python3
"""Review the staged source tree for accidentally published local artifacts."""
import hashlib
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_DIRS = {'input','evidence','runtime','vendor','publish','dist','node_modules','__pycache__'}
GENERATED = {'.exe','.dll','.bin','.obj','.bmd','.smd','.png','.jpg','.zip','.dmp','.mdmp','.dylib','.so','.o','.pyc','.orig','.new'}


# Owner-requested README screenshots and renders (reviewed 2026-10-21: window-only,
# no account names, passwords or private paths). Only these exact bytes are
# documentation media; all other binary/generated inputs remain rejected.
REVIEWED_MEDIA = {
    'docs/images/01-hero-lorencia-players-hud.jpg':
        'd589cd1764c8c9091f58566b4328700747e67de4aba69865708847525bbe380e',
    'docs/images/02-login-server-select.jpg':
        '776da4029a6a28b9035aac4c4e94f68252f93d964bcfb3aa3764b4518a89e52d',
    'docs/images/03-character-select.jpg':
        'baa322ab81fe62e3cf9c88cab013cb1ae4a1eacfeab302352bf8e02c4e6adb62',
    'docs/images/04a-character-creation.png':
        'fa926cbb24648bb01dca67407e7fdf956a72dd657dd355617738903f0bfade5f',
    'docs/images/04b-character-creation-all-classes.jpg':
        '2bd8ab20a3e1e61176b9cc158489002980613c53a7d63334e3c86cad5b90964a',
    'docs/images/05-world-atlans-devias-noria-lorencia.jpg':
        '841301b782b624ec660d3cff057f874b7575846070faa56b5529b87b3a626bfe',
    'docs/images/06-effects-skills-particles.jpg':
        '37676aefe584725848b1f83dbcdf8302ac68725f2403ddddc49e621e5415a281',
    'docs/images/07-gfx-character-window-buffs.png':
        '30dbbd94ab0177632cc587fb95e586e932e68ca46eb86544977c2c6588cb46f6',
    'docs/images/08-inventory-item-tooltip.png':
        'c2327e22b2baa9b99b5909b3e956f71a49cc5256d0f45743b8ca52bde28495ec',
    'docs/images/09-npc-dialogue-and-shop.jpg':
        'bd64fa6dd222b632553718032632a2e87a6c04d324b4a385d7af0f076a4bf306',
    'docs/images/10-combat-damage-numbers.jpg':
        '1b052daafbaf9187f7fc5f71ee8b65d925603ec25d34f20b0d2ae61a7031e074',
    'docs/images/12-pets-and-mounts.jpg':
        '4b81b6b5655b46652b203b706b94aa902cb6d2dc50d9acc876fa2df20c2acdc8',
    'docs/images/13-quests-my-quests.png':
        '8a01e27970b23388c99ec4b0ff0bb8a83292c33299033449e3b06cc2dadb921d',
    'docs/images/14-skill-imprint-window.png':
        'dce99e7f9123e6c27352d22e72f6336946e423d206c371c5751898789b5bbc8c',
    'docs/images/15-lorencia-lighting-live-before-after.jpg':
        'b45eab14a3a9e7ce8c527e8dacef46a25319fdca2d6f8a6e87ea848a4fb9a0ab',
    'docs/images/16-login-live-wine-vs-native.jpg':
        '97da9a148c44aa6213bc981d185c8ff6371c89dcee6967693f179910e75292b8',
    'docs/images/17-model-viewer-models.jpg':
        'fd2f3742172a9f1879b7970f7b2222acbc1953d77381a4cd539634d9e4997d3c',
}


def violations(name, content):
    path = pathlib.PurePosixPath(name)
    if name in REVIEWED_MEDIA and hashlib.sha256(content).hexdigest() == REVIEWED_MEDIA[name]:
        return []
    errors = []
    if any(part in PRIVATE_DIRS or part.startswith('verified') for part in path.parts):
        errors.append('local/generated directory')
    if name.startswith('mac-play/hotpatch/') and path.name in {'hotpatches.h','inlinesites.h','peepsites.h','orig.h','xform-prologue.h','meshdraw-orig.h'}:
        errors.append('private generated game-byte table')
    if path.suffix.lower() in GENERATED:
        errors.append('binary or generated asset type')
    if len(content) > 512*1024:
        errors.append('file exceeds reviewed source size limit')
    if b'\0' in content:
        errors.append('binary content')
    text = content.decode('utf-8',errors='replace')
    if re.search(r'/Users/[A-Za-z0-9_.-]+/',text):
        errors.append('machine-specific home path')
    if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})',text):
        errors.append('GitHub credential pattern')
    if re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----',text):
        errors.append('private key marker')
    return errors


def main():
    names = subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    names = [name for name in names if name]
    if not names:
        raise SystemExit('No staged/tracked source files to audit')
    failures = []
    for name in names:
        content = subprocess.check_output(['git','show',':'+name],cwd=ROOT)
        errors = violations(name,content)
        if errors:
            failures.append((name,errors))
    for name,errors in failures:
        print(name+': '+', '.join(errors))
    print(f'Audited {len(names)} staged files; {len(failures)} rejected.')
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
