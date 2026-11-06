#!/usr/bin/env python3
"""Which validator rows and test modules a diff can affect (TEST-SPEED-001).

Used by ``run_validators.py --affected REF`` and ``run_test_suites.py --affected REF``. The diff is everything
that differs from the merge base of REF and HEAD: the commits since then plus staged, unstaged and untracked
files (``git diff --no-renames <merge-base>`` and ``git ls-files --others``), so a rename counts as both paths.

The mapping is deliberately conservative; it may select too much, never too little for the inputs it knows:

* a Python file depends on itself, on the repository modules it imports (closure, resolved next to it and in
  scripts/), on every path its string literals name (a file, or every file under a directory), and on every
  file whose base name it quotes (``'renderchar.c'``) or whose first two path parts it quotes as separate
  strings (``ROOT / 'reconstructed' / d`` with ``'objects'`` in a list);
* a make directory depends on everything under it except docs (``*.md``) and unit tests (``test_*.py``), and on
  every path its Makefile reaches with ``../`` (``../record-math``, ``../deps.mk``, ``RECON := ../reconstructed``);
* a native make target depends on every repository file and include directory its full dry run
  (``make -nB <target>``) names, every header its ``.d`` files list (when built), and the headers next to each
  compiled source or in an ``-I`` directory (when not built).

Shared infrastructure selects everything that uses it (``INFRA``); the callers add their own (pins.py and
run_validators.py for validators; the Makefiles and run_test_suites.py for test suites).
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
import functools
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]
INFRA = ('scripts/affected.py',)
NOT_BUILT = re.compile(r'(^|/)(test_[^/]*\.py|[^/]*\.md)$')   # never compiled into a make directory's output
MAKE_REF = re.compile(r'(?:(?<=-I)|(?<![\w./]))\.\./[\w.+-]+(?:/[\w.+-]+)*')
RULE = re.compile(r'^([^\s:#=$][^\s:=$]*)\s*::?(?![=])')   # "target: prerequisites" in a make database
MAX_REASONS = 3
HEADERS = {'.h', '.hh', '.hpp', '.inc', '.inl', '.def'}
SOURCES = {'.c', '.cc', '.cpp', '.m', '.mm'}
INCLUDE = re.compile(r'^\s*#\s*(?:include|import)\s*[<"]([^">]+)[">]', re.M)
# Code directories whose files are reached by import or by name: a string naming the whole directory (``ROOT /
# 'scripts'``) is a search path, not a dependency on every file in it.
SEARCH_DIRS = {'scripts', 'tests', 'native/tests'}
# Runners: recorded as a dependency when imported, never followed (they name every validator and suite).
NOT_FOLLOWED = {'scripts/run_validators.py', 'scripts/run_test_suites.py', 'scripts/affected.py'}


def git(*args: str, root: Path = ROOT) -> str:
    done = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f'affected: git {" ".join(args)} failed: {done.stderr.strip()}')
    return done.stdout


def merge_base(ref: str, root: Path = ROOT) -> str:
    return git('merge-base', ref, 'HEAD', root=root).strip()


def changed_files(ref: str, root: Path = ROOT) -> list[str]:
    """Repository-relative paths that differ between merge-base(REF, HEAD) and the working tree."""
    base = merge_base(ref, root)
    paths = set(git('diff', '--no-renames', '--name-only', base, root=root).split('\n'))
    untracked = set(git('ls-files', '--others', '--exclude-standard', root=root).split('\n'))
    paths |= {p for p in untracked if not ((root / p).is_symlink() and (root / p).is_dir())}
    return sorted(p for p in paths if p)


def rel(path: Path, root: Path = ROOT) -> str | None:
    """POSIX path relative to the repository, or None outside it (system headers, Homebrew)."""
    try:
        return Path(os.path.normpath(path)).relative_to(root).as_posix()
    except ValueError:
        return None


@dataclass
class Deps:
    """What a unit (a validator row, a test module) depends on, each with the reason it was added."""
    files: dict[str, str] = field(default_factory=dict)       # exact repository files
    dirs: dict[str, str] = field(default_factory=dict)        # every file below (except NOT_BUILT for make dirs)
    flat: dict[str, str] = field(default_factory=dict)        # headers directly inside (-I directories)
    names: dict[str, str] = field(default_factory=dict)       # quoted strings: base names and path parts
    built_dirs: set[str] = field(default_factory=set)         # dirs added as make directories (skip NOT_BUILT)

    def update(self, other: 'Deps') -> 'Deps':
        for key in ('files', 'dirs', 'flat', 'names'):
            mine = getattr(self, key)
            for k, v in getattr(other, key).items():
                mine.setdefault(k, v)
        self.built_dirs |= other.built_dirs
        return self

    def why(self, path: str) -> str | None:
        """The reason PATH is a dependency, or None."""
        if path in self.files:
            return self.files[path]
        parts = PurePosixPath(path).parts
        for i in range(len(parts) - 1, 0, -1):
            prefix = '/'.join(parts[:i])
            if prefix in self.dirs:
                if prefix in self.built_dirs and NOT_BUILT.search(path):
                    continue
                return self.dirs[prefix]
        parent = '/'.join(parts[:-1])
        if parent in self.flat and PurePosixPath(path).suffix in HEADERS:
            return self.flat[parent]
        name = parts[-1]
        if name in self.names:
            return self.names[name]
        if len(parts) > 2 and parts[0] in self.names and parts[1] in self.names:
            return f'quotes {parts[0]!r} and {parts[1]!r}'
        return None


# ---------------------------------------------------------------------------------------------
# Python files

@functools.lru_cache(maxsize=None)
def _parse_python(path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(imported module names, string literals) of a Python file."""
    try:
        text = path.read_text(errors='replace')
    except OSError:
        return (), ()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return (), tuple(re.findall(r"""['"]([^'"\n]{1,200})['"]""", text))
    imports, strings = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            imports.append(node.module)
            imports += [f'{node.module}.{alias.name}' for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level:
            imports += [alias.name for alias in node.names] + ([node.module] if node.module else [])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 300:
            strings.append(node.value)
    return tuple(imports), tuple(strings)


def _module_file(name: str, near: Path, root: Path) -> Path | None:
    parts = name.split('.')
    for base in (near, root / 'scripts'):
        for candidate in (base.joinpath(*parts).with_suffix('.py'), base.joinpath(*parts, '__init__.py')):
            if candidate.is_file():
                return candidate
    return None


def _string_path(text: str, near: Path, root: Path) -> Path | None:
    """A string literal that names an existing repository file or directory."""
    if '/' not in text or '\n' in text or text.startswith(('http:', 'https:', '/')) or '{' in text:
        return None
    text = text.strip().rstrip('/')
    for base in (root, near):
        candidate = Path(os.path.normpath(base / text))
        if rel(candidate, root) not in (None, '.', '') and candidate.exists():
            return candidate
    return None


@functools.lru_cache(maxsize=None)
def _direct(path: Path, root: Path) -> tuple[Deps, tuple[Path, ...]]:
    """One Python file on its own: (the paths and names it quotes, the repository Python files it reaches)."""
    me = rel(path, root)
    deps, nxt = Deps(), []
    imports, strings = _parse_python(path)
    for name in imports:
        module = _module_file(name, path.parent, root)
        if module is not None:
            nxt.append(module)
    for text in strings:
        # Keep target names even when an ignored build output already exists.
        if 2 < len(text) < 80 and not text.isspace() and '\n' not in text:
            deps.names.setdefault(text, f'{me} quotes {text!r}')
        target = _string_path(text, path.parent, root)
        if target is not None:
            where = rel(target, root)
            if target.is_dir():
                if where not in SEARCH_DIRS:
                    deps.dirs.setdefault(where, f'{me} names {where}/')
            else:
                deps.files.setdefault(where, f'{me} names {where}')
                if target.suffix == '.py':
                    nxt.append(target)
        elif 2 < len(text) < 80 and not text.isspace() and '\n' not in text:
            deps.names.setdefault(text, f'{me} quotes {text!r}')   # incl. paths not built yet (build/mu-walk)
    return deps, tuple(dict.fromkeys(nxt))


@functools.lru_cache(maxsize=None)
def _closure(path: Path, root: Path) -> Deps:
    me = rel(path, root)
    out = Deps()
    if me is None or not path.is_file():
        return out
    out.files[me] = f'is {me}'
    queue, seen = [(path, None)], {path}
    while queue:
        current, via = queue.pop(0)
        name = rel(current, root)
        if via is not None:
            out.files.setdefault(name, f'imports {name}' + ('' if via == me else f' (via {via})'))
            if name in NOT_FOLLOWED:
                continue
        direct, nxt = _direct(current, root)
        for key in ('files', 'dirs', 'names'):
            table = getattr(out, key)
            for k, v in getattr(direct, key).items():
                table.setdefault(k, v)
        for module in nxt:
            if module not in seen and rel(module, root) is not None:
                seen.add(module)
                queue.append((module, name))
    return out


def python_deps(path: Path, root: Path = ROOT) -> Deps:
    """A Python file's dependencies: itself, the repository files it imports or names (closure), the paths and
    names they quote. A fresh copy: callers may add to it."""
    cached = _closure(Path(os.path.normpath(path)), root)
    return Deps(dict(cached.files), dict(cached.dirs), dict(cached.flat), dict(cached.names), set(cached.built_dirs))


# ---------------------------------------------------------------------------------------------
# make directories and targets

def makefile_deps(directory: str, root: Path = ROOT) -> Deps:
    """A make directory: all of it (but docs and tests) and everything its Makefile reaches with ../."""
    deps = Deps()
    deps.dirs[directory] = f'builds {directory}'
    deps.built_dirs.add(directory)
    base = root / directory
    makefile = base / 'Makefile'
    if not makefile.is_file():
        return deps
    for ref in sorted(set(MAKE_REF.findall(makefile.read_text(errors='replace')))):
        target = Path(os.path.normpath(base / ref))
        where = rel(target, root)
        if where in (None, '', '.') or not target.exists():
            continue
        if target.is_dir():
            deps.dirs.setdefault(where, f'{directory}/Makefile uses {where}/')
            deps.built_dirs.add(where)
        else:
            deps.files.setdefault(where, f'{directory}/Makefile uses {where}')
            if target.suffix == '.py':
                deps.update(python_deps(target, root))
    return deps


@functools.lru_cache(maxsize=None)
def make_targets(directory: str, root: Path = ROOT) -> tuple[str, ...]:
    """The explicit targets of a make directory (its database, nothing run)."""
    done = subprocess.run(['make', '-C', str(root / directory), '-pRrq', ':'], capture_output=True, text=True)
    targets, skip = set(), False
    for line in done.stdout.splitlines():
        if line.startswith('# Not a target'):
            skip = True
            continue
        rule = RULE.match(line)
        if rule:
            if not skip and '%' not in rule.group(1) and not rule.group(1).startswith(('.', '/')):
                targets.add(rule.group(1))
            skip = False
        elif not line:
            skip = False
    return tuple(sorted(targets))


@functools.lru_cache(maxsize=None)
def _quoted_includes(path: Path) -> tuple[str, ...]:
    try:
        return tuple(INCLUDE.findall(path.read_text(errors='replace')))
    except OSError:
        return ()


def _includes(sources: tuple[Path, ...], include_dirs: tuple[Path, ...]) -> set[Path]:
    """Every repository file reached through #include from SOURCES (next to the including file, then the -I
    directories), whatever the #if around it: a superset of what the compiler reads, with no build needed."""
    found, queue = set(), list(sources)
    while queue:
        current = queue.pop()
        for name in _quoted_includes(current):
            for base in (current.parent, *include_dirs):
                candidate = Path(os.path.normpath(base / name))
                if candidate.is_file():
                    if candidate not in found:
                        found.add(candidate)
                        queue.append(candidate)
                    break
    return found


@functools.lru_cache(maxsize=None)
def target_deps(directory: str, target: str | None, root: Path = ROOT) -> Deps:
    """Every repository file a full rebuild of TARGET in DIRECTORY reads (make -nB dry run, .d files)."""
    base = root / directory
    command = ['make', '-C', str(base), '-nB'] + ([target] if target else [])
    done = subprocess.run(command, capture_output=True, text=True)
    label = f'make -C {directory} {target or "(default goal)"}'
    deps = Deps()
    deps.files[f'{directory}/Makefile'] = f'{label} uses {directory}/Makefile'
    # Included make fragments can change flags/rules without appearing in recipe output.
    deps.files.update(makefile_deps(directory, root).files)
    if done.returncode:
        return makefile_deps(directory, root)  # an incomplete dry run cannot prove independence
    outputs, sources, include_dirs = [], [], []
    for line in done.stdout.splitlines():
        try:
            words = shlex.split(line, comments=False)
        except ValueError:
            words = line.split()
        previous = ''
        for word in words:
            flag = ''
            if word in ('-I', '-o', '-include', '-MT', '-MF', '-isystem', '>'):
                previous = word
                continue
            if word.startswith('-I') and len(word) > 2:
                flag, word = '-I', word[2:]
            elif previous == '-I':
                flag = '-I'
            elif previous == '-o' or previous == '>':
                outputs.append(word)
                previous = ''
                continue
            elif previous in ('-isystem', '-MT', '-MF'):
                previous = ''
                continue
            previous = ''
            if word.startswith('-') or '$' in word:
                continue
            path = Path(os.path.normpath(base / word))
            where = rel(path, root)
            if where in (None, '', '.') or not path.exists():
                continue
            if path.is_dir():
                if flag == '-I' or path == base:
                    pass  # search path; the include closure below identifies actual headers
                else:
                    deps.dirs.setdefault(where, f'{label} reads {where}/')
            else:
                deps.files.setdefault(where, f'{label} compiles {where}')
                if path.suffix in SOURCES:
                    sources.append(path)
                elif path.suffix == '.py':
                    deps.update(python_deps(path, root))
            if flag == '-I' and path.is_dir():
                include_dirs.append(path)
    headers = _includes(tuple(sources), tuple(dict.fromkeys(include_dirs)))
    if any(re.search(r'^\s*#\s*(?:include|import)\s+[^<\"\s]', p.read_text(errors='replace'), re.M)
           for p in [*sources, *headers]):
        for directory_path in include_dirs:
            where = rel(directory_path, root)
            if where:
                deps.flat[where] = f'{label} has computed includes in {where}/'
    for header in headers:   # #include "..." (closure)
        where = rel(header, root)
        if where:
            deps.files.setdefault(where, f'{label} includes {where}')
    for output in outputs:   # BUILD-DEPS-001 .d files: the exact headers, once built
        out = base / output
        for dfile in {out.with_suffix('.d'), Path(str(out) + '.d')}:
            if dfile.is_file():
                text = dfile.read_text(errors='replace').replace('\\\n', ' ')
                for word in text.split():
                    if word.endswith(':'):
                        continue
                    path = Path(os.path.normpath(base / word))   # .d paths are relative to the make directory
                    where = rel(path, root)
                    if where and path.is_file():
                        deps.files.setdefault(where, f'{label} includes {where}')
    return deps


# ---------------------------------------------------------------------------------------------
# selection

def select(units: dict[str, Deps], changed: list[str], infra: dict[str, str] | None = None, mapped: tuple[str, ...] = ()) -> dict[str, list[str]]:
    """{unit: [reasons]} for every unit some changed path can affect. INFRA paths (and the caller's ``infra``,
    path -> description) select every unit."""
    shared = {path: 'shared infrastructure' for path in INFRA}
    shared.update(infra or {})
    hit_all = [f'{path}: {shared[path]} (selects everything)' for path in changed if path in shared]
    for path in changed:
        if path not in mapped and path not in shared and not any(deps.why(path) for deps in units.values()) and \
                not path.endswith('.md') and not path.startswith('docs/'):
            hit_all.append(f'{path}: unmapped input (selects everything)')
    out: dict[str, list[str]] = {}
    for name, deps in units.items():
        reasons = list(hit_all)
        for path in changed:
            if path in shared:
                continue
            reason = deps.why(path)
            if reason:
                reasons.append(f'{path}: {reason}')
        if reasons:
            out[name] = reasons
    return out


def show(selected: dict[str, list[str]], total: int, noun: str) -> str:
    lines = [f'affected: {len(selected)} of {total} {noun} selected']
    for name, reasons in selected.items():
        more = f' (+{len(reasons) - MAX_REASONS} more)' if len(reasons) > MAX_REASONS else ''
        lines.append(f'  {name}: ' + '; '.join(reasons[:MAX_REASONS]) + more)
    return '\n'.join(lines)
