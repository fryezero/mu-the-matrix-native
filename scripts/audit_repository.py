#!/usr/bin/env python3
"""Review the staged source tree for accidentally published local artifacts."""
import hashlib
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_DIRS = {'input','evidence','runtime','vendor','publish','dist','node_modules','__pycache__'}
GENERATED = {'.exe','.dll','.bin','.obj','.bmd','.smd','.png','.jpg','.zip','.dmp','.mdmp','.dylib','.so','.o','.pyc','.orig','.new'}


# Owner-requested README screenshots and renders (reviewed 2026-10-21, 2026-10-22 and 2026-10-28: window-only,
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
        '9e4e83770afdfc01142add43ab4d6b9c7a315065ca45abeaa8200e9340d95fba',
    'docs/images/04b-character-creation-all-classes.jpg':
        '66a847ea9966a0c42a680ed15f26a853ff554ef1f51d6849c0060c00cb5bbe9b',
    'docs/images/05-world-atlans-devias-noria-lorencia.jpg':
        '841301b782b624ec660d3cff057f874b7575846070faa56b5529b87b3a626bfe',
    'docs/images/06-effects-skills-particles.jpg':
        '37676aefe584725848b1f83dbcdf8302ac68725f2403ddddc49e621e5415a281',
    'docs/images/07-gfx-character-window-buffs.png':
        '33fc8cbbf900f283ab8320331ef1faac9a795c93f6a59b621b3a07fe6b4a1c52',
    'docs/images/08-inventory-item-tooltip.png':
        '46c0bf6613ae14ea108fcc5682cb6da3e237123e0b138c83c29898c33a85d44a',
    'docs/images/09-npc-dialogue-and-shop.jpg':
        '626446e668f7257a012088ff39f98d07330628734ff04b097964e46dce97fac6',
    'docs/images/10-combat-damage-numbers.jpg':
        '1b052daafbaf9187f7fc5f71ee8b65d925603ec25d34f20b0d2ae61a7031e074',
    'docs/images/12-pets-and-mounts.jpg':
        '4b81b6b5655b46652b203b706b94aa902cb6d2dc50d9acc876fa2df20c2acdc8',
    'docs/images/13-quests-my-quests.png':
        '990c81b9088ea7c84acbe9335d71bea5880ff4ab931316dcd709628fee524450',
    'docs/images/14-skill-imprint-window.png':
        'de38484f80c6e13e375ff6f0de11d9e97ca8bd8745e0a9dfb19c122b9f0988ca',
    'docs/images/15-lorencia-lighting-live-before-after.jpg':
        'b45eab14a3a9e7ce8c527e8dacef46a25319fdca2d6f8a6e87ea848a4fb9a0ab',
    'docs/images/16-login-live-wine-vs-native.jpg':
        '97da9a148c44aa6213bc981d185c8ff6371c89dcee6967693f179910e75292b8',
    'docs/images/17-model-viewer-models.jpg':
        'fd2f3742172a9f1879b7970f7b2222acbc1953d77381a4cd539634d9e4997d3c',
    'docs/images/18-world-fidelity-live-before-after.jpg':
        '16a49ba3228884d4d0d8f9ead32f4e518cc186a3249289d32413f9752efa14cc',
    'docs/images/19-maps-tab-overlay-move-window.jpg':
        '31d407dcb6f93b8d88528bc4d8741229bb1410678aa2e2221355726001a7a125',
    'docs/images/20-skills-master-tree.jpg':
        '6a52d112ebb78bc54ab4e493e775094f26487415879cdd6ee2e79d362a8cd6ad',
    'docs/images/21-quests-guide-tracker.jpg':
        '6ee10241893ea63cb888d45464acf0b4b22fe55cfc993ac1c7a5608f6d1882f4',
    'docs/images/22-mounts-pets-effects.jpg':
        'd86aefa13b21112f04879073cd55bb3582b5eba042db99c457a48a5ad230caa8',
    'docs/images/23-chaos-goblin-mix-personal-store.jpg':
        'aee92f7af7fa2216d11b4a62a47484d674e47f5e771a8a8d72b16bffeef30376',
    'docs/images/24-social-party-trade-mail-whisper.jpg':
        'a8eefe1eb0a26f29ff661f3d1a72283339e53be16347dca2bd8dd7d0fc0f0df4',
    'docs/images/25-progression-character-options-menu.jpg':
        '139e45e8998d5a593b5b77bbdfc4332ebb9066aec4585ee184894d47713bf193',
    'docs/images/26-80-players-lorencia.jpg':
        'cad4e3993c3d72313f58e21230a7b9ec4b8085ef016f5b860ce7a1a4542e85d1',
    'docs/images/27-80-players-tormenta-combat.jpg':
        'a8386983e35fb5de8bb8315eb1e6d4057373729d373c2a33c9f94b02ec4b06b8',
}


# APP-POLISH-004: unresolved merge-conflict lines (#303's markers reached main in batch 42). Tracked text files
# that legitimately contain such lines are listed here, explicitly; none do today.
CONFLICT_MARKER = re.compile(r'^(?:<{7} |={7}\r?$|>{7} )', re.M)
CONFLICT_MARKER_EXEMPT = frozenset()


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
    if name not in CONFLICT_MARKER_EXEMPT and CONFLICT_MARKER.search(text):
        line = text.count('\n', 0, CONFLICT_MARKER.search(text).start()) + 1
        errors.append(f'merge conflict marker (line {line})')
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
