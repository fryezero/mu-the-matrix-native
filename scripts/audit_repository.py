#!/usr/bin/env python3
"""Review the staged source tree for accidentally published local artifacts."""
import hashlib
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRIVATE_DIRS = {'input','evidence','runtime','vendor','publish','dist','node_modules','__pycache__'}
GENERATED = {'.exe','.dll','.bin','.obj','.bmd','.smd','.png','.jpg','.zip','.dmp','.mdmp','.dylib','.so','.o','.pyc','.orig','.new'}


# Owner-requested README screenshots and GIFs. Only these exact reviewed bytes
# are documentation media; all other binary/generated inputs remain rejected.
REVIEWED_MEDIA = {
    'docs/media/login-live-vs-native.png':
        'ac965b789b734d5168b4b6b601afb3155899c6004b1d9c1dee279f6c119a2865',
    'docs/media/character-select-live-vs-native.png':
        '00c14a89064c9bfbf7ffb553b2d7b32d4a938304fb1ec9498dabab6b3103a0bc',
    'docs/media/lorencia-live-before-after.png':
        'dd2e01a1002711a71c2fc522e97c5b3f122987292be29c95aa9f4deed7c5071e',
    'docs/media/native-inventory.png':
        'c042bc9f805760d13c501208e11fcbc28b7d9d3f83a171ad1f8f86d664fa3262',
    'docs/media/native-login.gif':
        '16d98398477a6f7e1193b6095056ffc3c68eb01ef359dca99d325f412150c4a2',
    'docs/media/native-character-select.gif':
        'e9700a171e2441af775d0369f40293ec196b7a8f6f6ab07fb1d25d0474721de2',
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
