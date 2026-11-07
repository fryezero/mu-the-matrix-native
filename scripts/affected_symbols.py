#!/usr/bin/env python3
"""Which exported symbols of a compiled make target a diff changes (TEST-SPEED-005).

``affected.select`` asks this module before it selects a validator row only because a C source or header
changed inside a make target the row builds (``make -C D [target]`` compiles or includes the path, and nothing
else in the row names it). The answer is per linked artifact of the target's dry run (``make -nB``):

* Every translation unit the artifact links is compiled to LLVM IR (``-S -emit-llvm -O0 -g0``, the dry run's own
  flags) twice: on the working tree and on the base commit. The base side is the same command with a clang VFS
  overlay that maps each changed file to its base content, so only the files in the diff differ.
* Each function and global is a node with a fingerprint: its normalized IR (no metadata, attribute groups or
  comments; anonymous constants and function-local statics replaced by their content) plus the layout of every
  struct type it mentions. A struct layout change therefore changes every function that touches the struct.
  Edges are the symbols a node references (calls, address-taken functions, tables), resolved inside the
  artifact: internal names per translation unit, external names across them.
* A node is changed when its fingerprint differs or it exists on one side only. An exported symbol is changed
  when a changed node is reachable from it. ``main`` and ``llvm.global_ctors`` entries are reachable from every
  user (an executable runs main; constructors run on load).

The analysis gives up (the row is selected, with the reason, as a conservative fallback) when it cannot
attribute the change: a translation unit that does not compile to IR on either side, a link structure it
cannot map (prebuilt objects or archives, repository libraries, ``-undefined``/``-flat_namespace``), a changed
mutable global variable (global data counts for every user), a strong external definition that appears twice
in an artifact where it did not before (steward batch 2's duplicate ``mu_swamp_*``), or a new reference that
neither the artifact nor this process (libSystem) defines.
"""
from __future__ import annotations

import concurrent.futures
import ctypes
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

GLOBAL_NAME = r'@(?:"(?:[^"\\]|\\.)*"|[-a-zA-Z$._][-a-zA-Z$._0-9]*|\d+)'
GLOBAL_REF = re.compile(GLOBAL_NAME)
TYPE_REF = re.compile(r'%(?:"(?:[^"\\]|\\.)*"|[-a-zA-Z$._][-a-zA-Z$._0-9]*)')
DEFINE = re.compile(r'^define\s+(.*?)(' + GLOBAL_NAME + r')\(')
DECLARE = re.compile(r'^declare\s+.*?(' + GLOBAL_NAME + r')\(')
GLOBAL_DEF = re.compile(r'^(' + GLOBAL_NAME + r')\s*=\s*(.*)$')
TYPE_DEF = re.compile(r'^(%(?:"(?:[^"\\]|\\.)*"|[-a-zA-Z$._][-a-zA-Z$._0-9]*))\s*=\s*type\s*(.*)$')
METADATA = re.compile(r',?\s*!(?:[A-Za-z_][\w.]*)\s+!\d+|,?\s*!(?:[A-Za-z_][\w.]*)\s+!\{[^}]*\}')
ATTRIBUTE_REF = re.compile(r'\s#\d+\b')
PREDS = re.compile(r'\s+;.*$')
LOCAL_LINKAGE = {'internal', 'private'}
WEAK_LINKAGE = {'linkonce', 'linkonce_odr', 'weak', 'weak_odr', 'common', 'available_externally', 'extern_weak'}
LINKAGES = LOCAL_LINKAGE | WEAK_LINKAGE | {'external', 'appending'}
COMPILE_TIMEOUT = 300
JOBS = 2   # brief resource limit for parallel helpers
COMPILERS = {'cc', 'clang', 'gcc', 'c++', 'clang++', 'g++'}


def _bare(name: str) -> str:
    """'@"x y"' / '@x' -> 'x y' / 'x'."""
    name = name[1:]
    if name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    return name


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode('utf-8', 'surrogateescape')).hexdigest()[:16]


@dataclass
class Node:
    name: str
    kind: str                 # 'func', 'var' (mutable global), 'const', 'alias'
    linkage: str              # 'local', 'weak', 'strong'
    text: str                 # the raw definition
    fingerprint: str = ''
    refs: set = field(default_factory=set)    # bare global names referenced (after anonymous expansion)


@dataclass
class Unit:
    """One translation unit's IR facts."""
    source: str
    nodes: dict = field(default_factory=dict)        # bare name -> Node (named, non-anonymous)
    declared: set = field(default_factory=set)       # names declared, not defined
    ctors: set = field(default_factory=set)          # names in llvm.global_ctors / global_dtors
    error: str | None = None


def _anonymous(name: str, linkage: str) -> bool:
    """Compiler-named or function-local globals, renumbered whenever an unrelated one is added: .str.12,
    __const.f.v.1, switch.table.f, f.burst (a static local), .compoundliteral."""
    return name.startswith('.') or name.startswith(('__const.', 'switch.table.')) or \
        (linkage == 'local' and '.' in name)


def _strip_suffix(name: str) -> str:
    return re.sub(r'\.\d+$', '', name)


def parse_ir(text: str, source: str) -> Unit:
    unit = Unit(source)
    types: dict[str, str] = {}
    raw: dict[str, tuple[str, str, str]] = {}     # name -> (kind, linkage, text)
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('define'):
            body = [line]
            i += 1
            while i < len(lines) and lines[i] != '}':
                body.append(lines[i])
                i += 1
            body.append('}')
            match = DEFINE.match(line)
            if match:
                words = set(match.group(1).split())
                name = _bare(match.group(2))
                raw[name] = ('func', _linkage(words), '\n'.join(body))
        elif line.startswith('declare'):
            match = DECLARE.match(line)
            if match:
                unit.declared.add(_bare(match.group(1)))
        elif line.startswith('%'):
            match = TYPE_DEF.match(line)
            if match:
                types[match.group(1)] = match.group(2).strip()
        elif line.startswith('@'):
            match = GLOBAL_DEF.match(line)
            if match:
                name, rest = _bare(match.group(1)), match.group(2)
                words = rest.split()
                if name in ('llvm.global_ctors', 'llvm.global_dtors'):
                    unit.ctors |= {_bare(r) for r in GLOBAL_REF.findall(rest)}
                elif not name.startswith('llvm.'):
                    head = set(words[:8])
                    if 'alias' in head or 'ifunc' in head:
                        kind = 'alias'
                    elif 'constant' in head:
                        kind = 'const'
                    else:
                        kind = 'var'
                    linkage = _linkage(head)
                    if words and words[0] in ('external', 'extern_weak'):
                        unit.declared.add(name)   # LLVM prints 'external' only on declarations
                    else:
                        raw[name] = (kind, linkage, line)
        i += 1
    anonymous = {n for n, (_, linkage, _) in raw.items() if _anonymous(n, linkage)}
    canon_cache: dict[str, tuple[str, frozenset]] = {}
    type_cache: dict[str, str] = {}

    def type_layout(name: str, stack: tuple = ()) -> str:
        if name in type_cache:
            return type_cache[name]
        if name in stack or name not in types:
            return name
        body = types[name]
        inner = TYPE_REF.sub(lambda m: (type_layout(m.group(0), stack + (name,))
                                        if 'anon' in m.group(0) and m.group(0) in types else m.group(0)), body)
        type_cache[name] = inner
        return inner

    def mentioned_types(text: str) -> list[str]:
        """Every named type TEXT mentions, closed over the types their layouts mention: 'name=layout'."""
        seen, queue = set(), [t for t in TYPE_REF.findall(text) if t in types]
        while queue:
            t = queue.pop()
            if t in seen:
                continue
            seen.add(t)
            queue += [u for u in TYPE_REF.findall(types[t]) if u in types and u not in seen]
        return sorted(f'{_type_name(t)}={type_layout(t)}' for t in seen)

    def normalize(text: str, stack: tuple = ()) -> tuple[str, frozenset]:
        """TEXT without metadata, attribute groups and comments, with anonymous globals replaced by their
        content; and the named globals it references (through those anonymous ones too)."""
        text = METADATA.sub('', text)
        text = ATTRIBUTE_REF.sub('', text)
        text = '\n'.join(PREDS.sub('', line) if not line.lstrip().startswith(';') else ''
                         for line in text.split('\n')).strip()
        text = TYPE_REF.sub(lambda m: ('%{' + type_layout(m.group(0)) + '}') if 'anon' in m.group(0) and
                            m.group(0) in types else _type_name(m.group(0)) if m.group(0) in types else m.group(0),
                            text)
        refs: set[str] = set()

        def replace(match):
            name = _bare(match.group(0))
            if name in anonymous and name not in stack:
                content, inner = canon(name, stack)
                refs.update(inner)
                return '@{' + content + '}'
            if not name.startswith('llvm.'):
                refs.add(name)
            return match.group(0)
        return GLOBAL_REF.sub(replace, text), frozenset(refs)

    def canon(name: str, stack: tuple = ()) -> tuple[str, frozenset]:
        if name in canon_cache:
            return canon_cache[name]
        kind, linkage, text = raw[name]
        definition = text.split('=', 1)[1] if kind != 'func' else text
        content, refs = normalize(definition, stack + (name,))
        if not name.startswith('.') and not name.startswith(('__const.', 'switch.table.')):
            content = _strip_suffix(name) + ':' + content   # a static local keeps its (unnumbered) name
        result = (_hash(content + '|' + '|'.join(mentioned_types(text))), refs)
        canon_cache[name] = result
        return result

    for name, (kind, linkage, text) in raw.items():
        if name in anonymous:
            continue
        content, refs = normalize(text)
        if kind != 'func':
            content = content.split('=', 1)[1] if '=' in content else content
        node = Node(name, kind, linkage, text, refs=set(refs) - {name})
        node.fingerprint = _hash(content + '\n' + '\n'.join(mentioned_types(text)))
        unit.nodes[name] = node
    # A mutable static local (anonymous, 'var') is state: it counts as global data like any mutable global.
    # Keyed by its unnumbered name and content, so renumbering alone is no change.
    for name in anonymous:
        kind, linkage, text = raw[name]
        if kind == 'var':
            fingerprint, refs = canon(name)
            key = f'{_strip_suffix(name)}#{fingerprint}'
            unit.nodes[key] = Node(key, 'var', 'local', text, fingerprint, set(refs))
    unit.declared -= set(raw)
    return unit


def _type_name(name: str) -> str:
    return re.sub(r'\.\d+$', '', name)


def _linkage(words: set) -> str:
    if words & LOCAL_LINKAGE:
        return 'local'
    if words & WEAK_LINKAGE:
        return 'weak'
    return 'strong'


# ---------------------------------------------------------------------------------------------
# compiling to IR

def _ir_flags(flags: tuple[str, ...]) -> list[str]:
    """The dry run's compile flags for IR output: warnings off (-Werror must not fail the analysis), no
    optimization (explicit call edges, stable bodies), no debug info."""
    out, skip = [], False
    for word in flags:
        if skip:
            skip = False
            continue
        if word in ('-MT', '-MF', '-MQ', '-o'):
            skip = True
            continue
        if word in ('-MMD', '-MD', '-MP', '-shared', '-dynamiclib', '-c') or word.startswith(('-Werror', '-g')):
            continue
        out.append(word)
    return out + ['-w', '-O0', '-g0', '-S', '-emit-llvm', '-o', '-']


def compile_ir(cwd: str, flags: tuple[str, ...], source: str, overlay: str | None = None) -> Unit:
    command = _ir_flags(flags) + (['-ivfsoverlay', overlay] if overlay else []) + [source]
    try:
        done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, errors='surrogateescape',
                              timeout=COMPILE_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        unit = Unit(source)
        unit.error = f'{source} does not compile to IR ({error.__class__.__name__})'
        return unit
    if done.returncode:
        unit = Unit(source)
        first = next((line for line in done.stderr.splitlines() if 'error' in line), done.stderr.strip()[:200])
        unit.error = f'{source} does not compile to IR ({first.strip()[:200]})'
        return unit
    return parse_ir(done.stdout, source)


def write_overlay(folder: Path, mapping: dict[str, bytes | None]) -> str:
    """A clang VFS overlay (YAML is JSON) that serves MAPPING's absolute paths with the given contents."""
    by_dir: dict[str, list] = {}
    for index, (path, content) in enumerate(sorted(mapping.items())):
        if content is None:
            continue
        stored = folder / f'f{index}{os.path.splitext(path)[1]}'
        stored.write_bytes(content)
        directory, name = os.path.split(path)
        by_dir.setdefault(directory, []).append({'type': 'file', 'name': name, 'external-contents': str(stored)})
    roots = [{'type': 'directory', 'name': d, 'contents': entries} for d, entries in sorted(by_dir.items())]
    overlay = folder / 'overlay.yaml'
    overlay.write_text(json.dumps({'version': 0, 'case-sensitive': 'false', 'use-external-names': False,
                                   'roots': roots}))
    return str(overlay)


# ---------------------------------------------------------------------------------------------
# the dry run's artifacts

@dataclass
class Artifact:
    output: str
    units: list = field(default_factory=list)      # (flags, source) compiled into it
    problem: str | None = None


def artifacts(commands: list[list[str]], parse_compile) -> tuple[list[Artifact], str | None]:
    """The linked outputs of a dry run (compile+link in one command, or objects then a link / an archive),
    each with the (flags, source) pairs it contains; or a reason the link structure cannot be mapped."""
    objects: dict[str, tuple] = {}      # object output -> (flags, source)
    archives: dict[str, list] = {}      # archive output -> [(flags, source)]
    out: list[Artifact] = []
    for words in commands:
        if not words:
            continue
        tool = os.path.basename(words[0])
        if tool in ('ar', 'libtool'):
            members = [w for w in words[1:] if w.endswith('.o')]
            target = next((w for w in words[1:] if w.endswith('.a')), None)
            if target is None:
                return [], f'unrecognized archive command ({" ".join(words[:4])} ...)'
            missing = [m for m in members if m not in objects]
            if missing:
                return [], f'{target} archives objects the dry run does not compile ({missing[0]})'
            archives[target] = [objects[m] for m in members]
            continue
        if tool in ('ld', 'ld64', 'lld'):
            return [], f'unrecognized link command ({" ".join(words[:4])} ...)'
        if tool not in COMPILERS or any(w in ('-MM', '-M', '-E') for w in words):
            continue
        parsed = parse_compile(words)
        flags, sources = parsed if parsed is not None else ((), ())
        output = words[words.index('-o') + 1] if '-o' in words[:-1] else 'a.out'
        if '-c' in words:
            if len(sources) == 1:
                objects[output] = (flags, sources[0])
            else:
                for source in sources:
                    objects[os.path.splitext(os.path.basename(source))[0] + '.o'] = (flags, source)
            continue
        if not sources and not any(w.endswith(('.o', '.a')) for w in words[1:]):
            continue   # e.g. 'cc --version'
        artifact = Artifact(output, [(flags, s) for s in sources])
        operands = {i + 1 for i, w in enumerate(words) if w in ('-o', '-install_name', '-MT', '-MF', '-MQ')}
        for word in (w for i, w in enumerate(words) if i and i not in operands):
            if word.endswith('.o'):
                if word not in objects:
                    artifact.problem = f'{output} links an object the dry run does not compile ({word})'
                else:
                    artifact.units.append(objects[word])
            elif word.endswith('.a'):
                if word not in archives:
                    artifact.problem = f'{output} links an archive the dry run does not build ({word})'
                else:
                    artifact.units += archives[word]
            elif word.endswith(('.dylib', '.so', '.tbd')) or word.startswith('-L') or \
                    word in ('-undefined', '-flat_namespace', '-bundle_loader') or \
                    word.startswith(('-Wl,-undefined', '-Wl,-flat_namespace')):
                if not word.startswith('-L/opt/homebrew') and not word.startswith('-L/usr'):
                    artifact.problem = f'{output} links with {word}'
        out.append(artifact)
    linked = {u for a in out for u in a.units}
    for target, members in archives.items():
        if not any(set(members) <= set(a.units) for a in out):
            out.append(Artifact(target, list(members)))   # an archive is itself an output of the target
    loose = [u for u in objects.values() if u not in linked and not any(u in m for m in archives.values())]
    if loose:
        out.append(Artifact('(objects)', loose))
    return out, None


# ---------------------------------------------------------------------------------------------
# the analysis

@dataclass
class Change:
    """What a diff changes in one make target."""
    label: str
    fallback: str | None = None                        # why the change cannot be attributed (select all)
    changed: dict = field(default_factory=dict)        # exported name -> a changed node it reaches
    roots_always: set = field(default_factory=set)     # main / constructors that reach a change
    exports: set = field(default_factory=set)          # every externally visible name (both sides)
    removed: set = field(default_factory=set)          # exported on the base side only
    link_changed: str | None = None                    # a unit added, or a new reference across units


_PROCESS = ctypes.CDLL(None)
_IR: dict[tuple, Unit] = {}   # (cwd, flags, source, 'head' or the base side's key) -> its IR facts


def clear_cache(root: Path | None = None) -> None:
    for key in [k for k in _IR if root is None or k[0].startswith(str(root))]:
        del _IR[key]


def resolves_in_process(name: str) -> bool:
    """A symbol libSystem (libc, libm) or another library this process loaded defines."""
    try:
        getattr(_PROCESS, name)
        return True
    except AttributeError:
        return False


def _artifact_graph(units: list[Unit]):
    """(nodes {key: Node}, key of each external name, strong definition counts, undefined references)."""
    nodes, external, strong, referenced = {}, {}, {}, set()
    for unit in units:
        for name, node in unit.nodes.items():
            key = f'{unit.source}::{name}' if node.linkage == 'local' else name
            if node.linkage == 'strong':
                strong[name] = strong.get(name, 0) + 1
            if node.linkage != 'local':
                external.setdefault(name, key)
            nodes.setdefault(key, node)
        referenced |= unit.declared
    undefined = {n for n in referenced if n not in external and not n.startswith('llvm.')}
    return nodes, external, strong, undefined


def _edges(units: list[Unit], external: dict) -> dict[str, set]:
    out: dict[str, set] = {}
    for unit in units:
        for name, node in unit.nodes.items():
            key = f'{unit.source}::{name}' if node.linkage == 'local' else name
            targets = out.setdefault(key, set())
            for ref in node.refs:
                local = unit.nodes.get(ref)
                if local is not None and local.linkage == 'local':
                    targets.add(f'{unit.source}::{ref}')
                elif ref in external:
                    targets.add(external[ref])
    return out


def compare(label: str, head: list[list[Unit]], base: list[list[Unit]], names: list[str]) -> Change:
    """HEAD and BASE: per artifact (NAMES), its units on each side."""
    change = Change(label)
    for artifact, head_units, base_units in zip(names, head, base):
        broken = next((u.error for u in head_units + base_units if u.error), None)
        if broken:
            change.fallback = f'{artifact}: {broken}'
            return change
        h_nodes, h_external, h_strong, h_undefined = _artifact_graph(head_units)
        b_nodes, b_external, b_strong, b_undefined = _artifact_graph(base_units)
        duplicate = sorted(n for n, c in h_strong.items() if c > 1 and b_strong.get(n, 0) < c)
        if duplicate:
            change.fallback = f'{artifact}: new duplicate definition of {duplicate[0]}' + (
                f' (+{len(duplicate) - 1})' if len(duplicate) > 1 else '')
            return change
        missing = sorted(n for n in h_undefined - b_undefined if not resolves_in_process(n))
        if missing:
            change.fallback = f'{artifact}: new unresolved reference to {missing[0]}' + (
                f' (+{len(missing) - 1})' if len(missing) > 1 else '')
            return change
        for head_unit, base_unit in zip(head_units, base_units):
            if change.link_changed:
                break
            if head_unit.nodes and not base_unit.nodes:
                change.link_changed = f'{artifact}: {head_unit.source} is new'
                continue
            across = sorted(n for n in head_unit.declared - base_unit.declared if n in h_external)
            if across:
                change.link_changed = f'{artifact}: {head_unit.source} newly calls {across[0]} from another unit'
        changed = {k for k in set(h_nodes) | set(b_nodes)
                   if (h_nodes.get(k).fingerprint if k in h_nodes else None) !=
                   (b_nodes.get(k).fingerprint if k in b_nodes else None)}
        data = sorted(k for k in changed if (h_nodes.get(k) or b_nodes.get(k)).kind == 'var')
        if data:
            change.fallback = f'{artifact}: global data changed ({data[0].split("::")[-1]})'
            return change
        edges = _edges(head_units, h_external)
        reverse: dict[str, set] = {}
        for key, targets in edges.items():
            for t in targets:
                reverse.setdefault(t, set()).add(key)
        reach: dict[str, str] = {k: k for k in changed}
        queue = sorted(changed)
        while queue:
            current = queue.pop()
            for user in reverse.get(current, ()):
                if user not in reach:
                    reach[user] = reach[current]
                    queue.append(user)
        exported_head = {n for n, k in h_external.items()}
        exported_base = {n for n, k in b_external.items()}
        change.exports |= exported_head | exported_base
        change.removed |= exported_base - exported_head
        for name in exported_head | exported_base:
            key = h_external.get(name, name)
            if key in reach:
                change.changed.setdefault(name, reach[key].split('::')[-1])
        always = {'main'} | {c for u in head_units + base_units for c in u.ctors}
        for name in always:
            key = h_external.get(name)
            if key is None:
                key = next((f'{u.source}::{name}' for u in head_units if name in u.nodes), None)
            if key is not None and key in reach:
                change.roots_always.add(name)
    return change


def analyze(label: str, cwd: Path, root: Path, commands: list[list[str]], parse_compile, base_files: dict,
            unit_inputs) -> Change:
    """The Change of one make target: COMMANDS its dry run, BASE_FILES {absolute path: base bytes or None}
    for every changed file, UNIT_INPUTS(flags, source) the repository files a unit reads (None: unknown)."""
    found, problem = artifacts(commands, parse_compile)
    if problem:
        return Change(label, fallback=problem)
    if not found:
        return Change(label, fallback='the dry run links nothing the analysis can map')
    broken = next((a.problem for a in found if a.problem), None)
    if broken:
        return Change(label, fallback=broken)
    pairs = list(dict.fromkeys(u for a in found for u in a.units))
    side = _hash(repr(sorted((p, _hash(c.decode('latin-1')) if c is not None else None)
                             for p, c in base_files.items())))
    with tempfile.TemporaryDirectory(prefix='affected-symbols-') as folder:
        overlay = write_overlay(Path(folder), base_files) if base_files else None
        changed_paths = set(base_files)

        def cached(flags, source, key, with_overlay):
            entry = (str(cwd), tuple(flags), source, key)
            if entry not in _IR:
                _IR[entry] = compile_ir(str(cwd), flags, source, overlay if with_overlay else None)
            return _IR[entry]

        def both(pair):
            flags, source = pair
            head = cached(flags, source, 'head', False)
            inputs = unit_inputs(flags, source)
            same = inputs is not None and not (set(inputs) & changed_paths)
            if same or overlay is None:
                return head, head
            absolute = os.path.realpath(os.path.join(str(cwd), source))
            if absolute in base_files and base_files[absolute] is None:
                return head, Unit(source)   # added since the base: nothing on the base side
            return head, cached(flags, source, side, True)
        with concurrent.futures.ThreadPoolExecutor(JOBS) as pool:
            results = dict(zip(pairs, pool.map(both, pairs)))
    head = [[results[u][0] for u in a.units] for a in found]
    base = [[results[u][1] for u in a.units] for a in found]
    return compare(label, head, base, [a.output for a in found])
