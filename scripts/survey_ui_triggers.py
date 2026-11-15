#!/usr/bin/env python3
"""Which kind of owner reaches a proved UI open site: a bounded caller-chain census.

For every open/toggle site of the route survey this walks direct relative callers upward, at most seven
functions, and records where each chain ends:

  server-response  the chain enters the receive dispatcher 0x01287ead (reconstructed/npc/npc_talk.h);
  table            the function's address is stored in the image data (a virtual method or callback table
                   entry); the address of the first such dword is kept, not a guessed class or callback name;
  uncalled         no direct caller and no data reference was found inside the bound.

Function starts are the nearest preceding `push ebp; mov ebp, esp`, a navigation heuristic. Indirect calls,
jump tables and callers beyond seven functions are not followed, so a missing kind is not proof of absence.
A root kind names the owner class of a trigger. It is not a route, a key, a packet layout or a permission
to execute the owner. Outputs contain addresses and reviewed classifications only, no captured bytes.
"""
import argparse
import bisect
import csv
import re
import struct
from pathlib import Path

import pins

TEXT_BASE = 0x401000
DATA_BASE = 0x1a7c000
DISPATCHER = 0x01287ead
DEPTH = 7


def index(text, data):
    """Direct call edges, function-start candidates and text pointers stored in the image data."""
    callers = {}
    for match in re.finditer(b'\xe8', text):
        at = match.start()
        if at+5 <= len(text):
            target = TEXT_BASE+at+5+struct.unpack_from('<i', text, at+1)[0]
            if TEXT_BASE <= target < TEXT_BASE+len(text):
                callers.setdefault(target, []).append(TEXT_BASE+at)
    starts = sorted(TEXT_BASE+m.start() for m in re.finditer(b'\x55\x8b\xec', text))
    stored = {}
    for at in range(0, len(data)-3, 4):
        value = struct.unpack_from('<I', data, at)[0]
        if TEXT_BASE <= value < TEXT_BASE+len(text):
            stored.setdefault(value, DATA_BASE+at)
    return callers, starts, stored


def function_of(starts, address):
    at = bisect.bisect_right(starts, address)-1
    return starts[at] if at >= 0 else None


def roots(site, callers, starts, stored, dispatcher=DISPATCHER, depth=DEPTH):
    """{kind: shortest chain found} for one site; a chain lists call sites from the open upward."""
    found, seen = {}, set()
    work = [(function_of(starts, site), [site])]
    while work:
        function, chain = work.pop(0)
        if function is None or function in seen or len(chain) > depth:
            continue
        seen.add(function)
        if function == dispatcher:
            found.setdefault('server-response', chain)
            continue
        sites = callers.get(function, [])
        if function in stored:
            found.setdefault('table', chain+[stored[function]])
        if not sites and function not in stored:
            found.setdefault('uncalled', chain+[function])
        for caller in sites:
            work.append((function_of(starts, caller), chain+[caller]))
    return found


def survey_rows(survey, classes):
    with open(survey, newline='') as f:
        return [r for r in csv.DictReader(f) if r['classification'] in classes and r['open_sites']]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--survey', type=Path, default=pins.REPO/'docs/research/ui-window-route-survey.csv')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    callers, starts, stored = index(pins.TEXT.read(), pins.DATA.read())
    rows = []
    for r in survey_rows(args.survey, ('route proved + provider missing', 'route proved + provider complete',
                                       'state-dependent')):
        for site in r['open_sites'].split(';'):
            found = roots(int(site, 16), callers, starts, stored)
            rows.append(dict(movie=r['movie'], classification=r['classification'], site=site,
                             function=f"0x{function_of(starts, int(site, 16)):08x}",
                             roots=';'.join(sorted(found)) or 'none in bound',
                             chains=' | '.join(k+': '+' <- '.join(f'0x{a:08x}' for a in found[k]) for k in sorted(found))))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['movie', 'classification', 'site', 'function', 'roots', 'chains'],
                           lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    kinds = {}
    for row in rows:
        kinds[row['roots']] = kinds.get(row['roots'], 0)+1
    print({'sites': len(rows), 'by_roots': kinds})


if __name__ == '__main__':
    main()
