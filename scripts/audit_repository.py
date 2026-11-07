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
        'be1c3d696b16764ec192d4e508fbb3fba5be284061add1b75328adda5c19bf6d',
    'docs/images/02-login-server-select.jpg':
        '776da4029a6a28b9035aac4c4e94f68252f93d964bcfb3aa3764b4518a89e52d',
    'docs/images/03-character-select.jpg':
        'baa322ab81fe62e3cf9c88cab013cb1ae4a1eacfeab302352bf8e02c4e6adb62',
    'docs/images/04a-character-creation.png':
        'fa926cbb24648bb01dca67407e7fdf956a72dd657dd355617738903f0bfade5f',
    'docs/images/04b-character-creation-all-classes.jpg':
        '2bd8ab20a3e1e61176b9cc158489002980613c53a7d63334e3c86cad5b90964a',
    'docs/images/05-world-atlans-devias-noria-lorencia.jpg':
        '683c5f41ef31380f23baad028346485456ede5cbdb77f63f52be8b97bee59007',
    'docs/images/06-effects-skills-particles.jpg':
        'ef05b5b07c27a2445e8dd8bd12dd27cf78c8eb2b73e940efbcf20b8cbb411b34',
    'docs/images/07-gfx-character-window-buffs.png':
        '30dbbd94ab0177632cc587fb95e586e932e68ca46eb86544977c2c6588cb46f6',
    'docs/images/08-inventory-item-tooltip.png':
        'c2327e22b2baa9b99b5909b3e956f71a49cc5256d0f45743b8ca52bde28495ec',
    'docs/images/09-npc-dialogue-and-shop.jpg':
        'bd64fa6dd222b632553718032632a2e87a6c04d324b4a385d7af0f076a4bf306',
    'docs/images/10-combat-damage-numbers.jpg':
        '5d6faaff7cd4157287f5366461b82da74ce06c6aaea0b0b5549c0a536043b080',
    'docs/images/12-pets-and-mounts.jpg':
        'b73721697bf83c0b66d333d986308b3ac6be4827982855c57fc943a65177e5e4',
    'docs/images/13-quests-my-quests.png':
        '8a01e27970b23388c99ec4b0ff0bb8a83292c33299033449e3b06cc2dadb921d',
    'docs/images/14-skill-imprint-window.png':
        'dce99e7f9123e6c27352d22e72f6336946e423d206c371c5751898789b5bbc8c',
    'docs/images/15-lorencia-lighting-live-before-after.jpg':
        '279935ce032fe7f880bf40be37f81dc4e0fb931a9fd864ce0f517bc48ab246b3',
    'docs/images/16-login-live-wine-vs-native.jpg':
        '97da9a148c44aa6213bc981d185c8ff6371c89dcee6967693f179910e75292b8',
    'docs/images/17-model-viewer-models.jpg':
        'fd2f3742172a9f1879b7970f7b2222acbc1953d77381a4cd539634d9e4997d3c',
    'docs/images/18-world-fidelity-live-before-after.jpg':
        'b3a5198ed7bc65ed61ca1c219e46c7ab7afd3a4923580987022382eed69d72e9',
    'docs/images/19-maps-tab-overlay-move-window.jpg':
        'c6ee4c9d87b1330cfebc751dd64c3f34a496b85e2f0997b3d180365d9a5a2c80',
    'docs/images/20-skills-master-tree.jpg':
        '9e40314a7cf9a185138e55a8fb10ceaaea26cf459216834708e13252df8d0eb1',
    'docs/images/21-quests-guide-tracker.jpg':
        '1dd861789a4b2692fdca8a6be1da4fac886258e29d3e1a72bdbc2f3b3bccea9d',
    'docs/images/22-mounts-pets-effects.jpg':
        '2980529b0e2053b956f76153d79757dfd0434b78515ae3189cc4e48a0ca2e7c0',
    'docs/images/23-chaos-goblin-mix-personal-store.jpg':
        'ae4cad0d54c97e3af15b9b5514a7fac91ae4e570822c5dbf61d1378e170b6ec3',
    'docs/images/24-social-party-trade-mail-whisper.jpg':
        '556cc31af55fc527713aec258651ddeed12f4aef0d619f61606a99ea2c244be3',
    'docs/images/25-progression-character-options-menu.jpg':
        'ce1ddc4822f24d33c6678160a83ff089d3905170d9ac99b71c42d16aa19b0435',
    'docs/images/26-80-players-lorencia.jpg':
        'cad4e3993c3d72313f58e21230a7b9ec4b8085ef016f5b860ce7a1a4542e85d1',
    'docs/images/27-80-players-tormenta-combat.jpg':
        'a8386983e35fb5de8bb8315eb1e6d4057373729d373c2a33c9f94b02ec4b06b8',
    'docs/images/28-bow-arrows-trails-sparks.jpg':
        'f100951b86afbb4014512a272c37f80cb4b092daf93c0262e69af46b6ecb48bf',
    'docs/images/29-ground-skill-rain-rings-craters.jpg':
        'd64c5586e38627995e659dd72f4eaddecf385de5cdd4094f7d1957b260d119a9',
    'docs/images/30-worlds-live-vs-native.jpg':
        '8e5c85f9a5fb2091855cc52d2de5f598bc5171aaf784b02cb4436bdded491e5d',
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
