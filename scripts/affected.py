#!/usr/bin/env python3
"""Which validator rows and test modules a diff can affect (TEST-SPEED-001, exact inputs since TEST-SPEED-004).

Used by ``run_validators.py --affected REF / --affected-since REF`` and ``run_test_suites.py`` (same flags).
``--affected REF`` diffs merge-base(REF, HEAD) against the working tree (a lane: "what did my branch change");
``--affected-since REF`` diffs REF itself against the working tree (the steward: "what changed since the
commit the lane tested"). Both count commits, staged, unstaged and untracked files, renames as both paths.

A unit (validator row, test module) is affected iff the diff touches one of its derived inputs:

* **Python**: the file, every repository module it imports (``sys.path`` directories it adds, ``importlib``
  loaders whose names come from constants or from the call sites of a local wrapper), and every repository path
  its code builds. Paths are folded from the code (``ROOT / 'reconstructed' / d`` with ``d`` from a constant
  loop, a constant assignment or every call site of the function), and each directory use is classified:
  ``make -C D [targets]`` → those targets' compiled inputs; ``-I D`` → the headers the compiled sources include;
  ``D.glob('x_*.c')`` → the matching files; ``sys.path`` → imports only; anything else → every file under D.
  A bare word (``'objects'`` as a memory-region name) is not a path; quoted file names (``'renderchar.c'``)
  still match by base name.
* **Compiled**: per make target, every file its full dry run (``make -nB``) compiles or reads, plus the headers
  of each compile: from its ``.d`` file when that is newer than everything it lists, else the compiler's own
  ``-MM -MG`` on the dry-run command, else a textual ``#include`` closure. A changed Makefile counts for a
  target only if the target's dry run differs between the base Makefile and the current one. A deleted file
  counts for every target that compiled files in its directory.
* **Tooling** (``TOOLING``): the runners, this selector and the original-side cache never select a validator
  row; their own unit tests (``tests``) cover them.

When a unit's inputs cannot be derived (a computed import, a path built from an unknown value at the
repository root, a module that does not parse) the unit records why (``Deps.fallback``) and is selected for
every code change; ``--list-affected`` prints those units so the set can shrink. See docs/testing/TEST-BUDGET.md.
"""
from __future__ import annotations

import ast
import concurrent.futures
from dataclasses import dataclass, field
import fnmatch
import functools
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import tempfile

import affected_symbols

ROOT = Path(__file__).resolve().parents[1]
# Gate/selection tooling: a change selects the tooling tests (the always-run `tests` suite: test_test_budget,
# test_validator_original_cache, test_validators_manifest, test_run_test_suites) and the modules that import
# or name the file, never a validator row. original_cache.py only decides cache keys; it never changes a
# validator's result (tests/test_validator_original_cache.py proves a warm cache still sees a changed C result).
TOOLING = {
    'scripts/affected.py': 'the affected-input selector',
    'scripts/run_validators.py': 'the validator runner',
    'scripts/run_test_suites.py': 'the suite runner',
    'scripts/original_cache.py': 'the original-side cache (cache keys only)',
    'scripts/guarded_run.py': 'a test-only launcher helper',
    'scripts/replay_affected.py': 'the selection replay (TEST-SPEED-004)',
    'scripts/affected_symbols.py': 'the symbol-level change analysis (TEST-SPEED-005)',
}
TOOLING_TESTS = ('tests/test_test_budget.py', 'tests/test_validator_original_cache.py',
                 'tests/test_validators_manifest.py', 'tests/test_run_test_suites.py')
INFRA: tuple[str, ...] = ()   # callers add their own (the top-level Makefile, the gate script)
NOT_BUILT = re.compile(r'(^|/)(test_[^/]*\.py|[^/]*\.md)$')   # never compiled into a make directory's output
MAKE_REF = re.compile(r'(?:(?<=-I)|(?<![\w./]))\.\./[\w.+-]+(?:/[\w.+-]+)*')
RULE = re.compile(r'^([^\s:#=$][^\s:=$]*)\s*::?(?![=])')   # "target: prerequisites" in a make database
MAX_REASONS = 3
HEADERS = {'.h', '.hh', '.hpp', '.inc', '.inl', '.def'}
SOURCES = {'.c', '.cc', '.cpp', '.m', '.mm'}
INCLUDE = re.compile(r'^\s*#\s*(?:include|import)\s*[<"]([^">]+)[">]', re.M)
FILE_NAME = re.compile(r'[\w+-][\w+.-]*\.(?:c|cc|cpp|m|mm|h|hh|hpp|inc|inl|def|py|mk|json|toml|txt|csv|tsv)')
# Code directories whose files are reached by import or by name: a string naming the whole directory (``ROOT /
# 'scripts'``) is a search path, not a dependency on every file in it.
SEARCH_DIRS = {'scripts', 'tests', 'native/tests'}
# Runners and the rest of the tooling: recorded as a dependency when imported (so their own tests are selected),
# never followed (they name every validator and suite, or hash arbitrary files).
NOT_FOLLOWED = {'scripts/run_validators.py', 'scripts/run_test_suites.py', 'scripts/affected.py', *TOOLING}
SYMBOL_FALLBACK = 'symbol fallback'   # marks a reason that kept a row because a change could not be attributed
ROOT_NAMES = {'ROOT', 'REPO', 'REPO_ROOT', 'REPOSITORY'}
COMPILERS = {'cc', 'clang', 'gcc', 'c++', 'clang++', 'g++'}


def _memo(function):
    """functools.lru_cache without a size limit, whose cache_clear(root) forgets only the calls about ROOT."""
    cache: dict = {}

    @functools.wraps(function)
    def wrapper(*args):
        try:
            return cache[args]
        except KeyError:
            value = cache[args] = function(*args)
            return value

    def cache_clear(root: Path | None = None):
        if root is None:
            cache.clear()
            return
        prefix = str(root)
        for key in [k for k in cache if any(str(a).startswith(prefix) for a in k if isinstance(a, (str, Path)))]:
            del cache[key]

    wrapper.cache_clear = cache_clear
    return wrapper


def git(*args: str, root: Path = ROOT) -> str:
    done = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f'affected: git {" ".join(args)} failed: {done.stderr.strip()}')
    return done.stdout


def merge_base(ref: str, root: Path = ROOT) -> str:
    return git('merge-base', ref, 'HEAD', root=root).strip()


def base_commit(ref: str, root: Path = ROOT, since: bool = False) -> str:
    """The commit a diff starts from: REF itself for --affected-since, else merge-base(REF, HEAD)."""
    return git('rev-parse', '--verify', f'{ref}^{{commit}}', root=root).strip() if since else merge_base(ref, root)


def changed_files(ref: str, root: Path = ROOT, since: bool = False) -> list[str]:
    """Repository-relative paths that differ between the base (see base_commit) and the working tree."""
    base = base_commit(ref, root, since)
    paths = set(git('diff', '--no-renames', '--name-only', base, root=root).split('\n'))
    untracked = set(git('ls-files', '--others', '--exclude-standard', root=root).split('\n'))
    paths |= {p for p in untracked if not ((root / p).is_symlink() and (root / p).is_dir())}
    return sorted(p for p in paths if p)


def rel(path: Path, root: Path = ROOT) -> str | None:
    """POSIX path relative to the repository, or None outside it (system headers, Homebrew)."""
    text, base = os.path.normpath(str(path)), str(root)
    if text == base:
        return ''
    return text[len(base) + 1:] if text.startswith(base + os.sep) else None


def _suffix(path: str) -> str:
    return os.path.splitext(path)[1]


def is_doc(path: str) -> bool:
    return path.startswith('docs/') or path.endswith('.md')


@dataclass
class Deps:
    """What a unit (a validator row, a test module) depends on, each with the reason it was added."""
    files: dict[str, str] = field(default_factory=dict)       # exact repository files
    dirs: dict[str, str] = field(default_factory=dict)        # every file below (except NOT_BUILT for make dirs)
    flat: dict[str, str] = field(default_factory=dict)        # headers directly inside (-I directories)
    names: dict[str, str] = field(default_factory=dict)       # quoted file names: base names or path suffixes
    words: set[str] = field(default_factory=set)              # every short quoted string (make target names)
    built_dirs: set[str] = field(default_factory=set)         # dirs added as make directories (skip NOT_BUILT)
    globs: dict[str, str] = field(default_factory=dict)       # fnmatch patterns over repository paths
    makefiles: dict[str, set] = field(default_factory=dict)   # Makefile -> {(dir, target)} whose dry run uses it
    src_dirs: dict[str, str] = field(default_factory=dict)    # directories a target compiles files from
    fallback: dict[str, str] = field(default_factory=dict)    # why the inputs are not fully derivable
    # TEST-SPEED-005: symbol-level use of make targets.
    targets: dict[str, set] = field(default_factory=dict)     # file -> {(dir, target)} whose build reads it
    other: set[str] = field(default_factory=set)              # files that are also inputs some other way
    symbols: set[str] = field(default_factory=set)            # identifiers the Python code names (exports used)
    sym_patterns: dict[str, str] = field(default_factory=dict)   # computed names: 'mu_*_move' -> where
    sym_dynamic: dict[str, str] = field(default_factory=dict)    # where -> a symbol name it cannot bound
    # Paths used only by mutant code (mutant builds compile copies of the library sources with a planted
    # change): still inputs, but they do not stop the symbol-level pruning of a file a make target compiles.
    mutant: 'Deps | None' = None

    def update(self, other: 'Deps') -> 'Deps':
        for k, v in other.files.items():
            if k in self.files:
                mine_make = k in self.targets and k not in self.other
                their_make = k in other.targets and k not in other.other
                if mine_make != their_make or (k in self.other) or (k in other.other):
                    self.other.add(k)
            elif k in other.other:
                self.other.add(k)
        for key in ('files', 'dirs', 'flat', 'names', 'globs', 'src_dirs', 'fallback', 'sym_patterns',
                    'sym_dynamic'):
            mine = getattr(self, key)
            for k, v in getattr(other, key).items():
                mine.setdefault(k, v)
        for k, v in other.makefiles.items():
            self.makefiles.setdefault(k, set()).update(v)
        for k, v in other.targets.items():
            self.targets.setdefault(k, set()).update(v)
        self.words |= other.words
        self.built_dirs |= other.built_dirs
        self.symbols |= other.symbols
        if other.mutant is not None:
            self.mutant = (self.mutant or Deps()).update(other.mutant)
        return self

    def add(self, path: str, reason: str) -> None:
        """An input that is not one of a make target's compiled files (the code names or compiles it)."""
        if path in self.targets:
            self.other.add(path)
        self.files.setdefault(path, reason)

    def copy(self) -> 'Deps':
        return Deps().update(self)

    def make_only(self, path: str, same_make: frozenset = frozenset(), root: Path | None = None) -> set:
        """The (dir, target) pairs that make PATH an input, if a make target's build is its only route (a
        candidate for symbol-level pruning); else an empty set."""
        if path not in self.targets or path in self.other or (path in self.makefiles):
            return set()
        if self._why(path, same_make, root, compiled=False) is not None:
            return set()
        return set(self.targets[path])

    def why(self, path: str, same_make: frozenset = frozenset(), root: Path | None = None) -> str | None:
        """The reason PATH is an input, or None. SAME_MAKE: (dir, target) pairs whose dry run a changed
        Makefile leaves identical. ROOT: when given, a path missing from it (deleted) counts for every target
        that compiles files from its directory."""
        found = self._why(path, same_make, root, compiled=True)
        if found is None and self.mutant is not None:
            found = self.mutant._why(path, same_make, root, compiled=True)
            if found is not None:
                found = f'mutant build: {found}'
        return found

    def mutant_route(self, path: str, same_make: frozenset = frozenset(), root: Path | None = None) -> bool:
        return self.mutant is not None and self.mutant._why(path, same_make, root, compiled=True) is not None

    def _why(self, path: str, same_make: frozenset, root: Path | None, compiled: bool) -> str | None:
        """COMPILED=False: only the routes other than a make target's compiled files and Makefile."""
        if compiled and path in self.makefiles:
            uses = sorted((d, t or '') for d, t in self.makefiles[path] if (d, t) not in same_make)
            if uses:
                d, t = uses[0]
                return f'make -C {d} {t or "(default goal)"} uses {path}' + (
                    f' (+{len(uses) - 1} targets)' if len(uses) > 1 else '')
        if path in self.files and (compiled or path not in self.targets or path in self.other):
            return self.files[path]
        parts = PurePosixPath(path).parts
        for i in range(len(parts) - 1, 0, -1):
            prefix = '/'.join(parts[:i])
            if prefix in self.dirs:
                if prefix in self.built_dirs and NOT_BUILT.search(path):
                    continue
                return self.dirs[prefix]
        parent = '/'.join(parts[:-1])
        if parent in self.flat and _suffix(path) in HEADERS:
            return self.flat[parent]
        name = parts[-1]
        if not is_doc(path):   # a quoted output name ('summary.json') is not a documentation input
            if name in self.names:
                return self.names[name]
            for suffix, reason in self.names.items():
                if '/' in suffix and path.endswith('/' + suffix):
                    return reason
        for pattern, reason in self.globs.items():
            # like a directory: its unit tests and docs are never read through a computed path, unless the
            # pattern itself names them ('tests/test_*.py')
            if fnmatch.fnmatchcase(path, pattern) and \
                    not (NOT_BUILT.search(path) and not NOT_BUILT.search(pattern.replace('*', 'x'))):
                return reason
        if root is not None and parent in self.src_dirs and not (root / path).exists() and \
                _suffix(path) in SOURCES | HEADERS:
            return f'deleted from {parent}/, which {self.src_dirs[parent]}'
        return None


# ---------------------------------------------------------------------------------------------
# Python files: imports and the repository paths the code builds
#
# Values are strings: 'S:<text>' a plain string, 'P:<path>' a repository path ('' is the root; '*' marks a part
# the analysis cannot know), 'A:<function key>\x1f<head>\x1f<tail>' a function parameter's value with known text
# around it (head is an 'S:'/'P:' value, tail plain text). A parameter's uses are resolved at every call site
# in the closure (Resolver), so ``build_library(ROOT / 'reconstructed')`` reaching ``make -C directory/'objects'``
# in another module is a use of ``make -C reconstructed/objects``.

LOADERS = {'spec_from_file_location': 1, 'SourceFileLoader': 1, 'import_module': 0, '__import__': 0,
           'run_path': 0, 'run_module': 0, 'load_source': 1}
WRAPPERS = {'str', 'Path', 'PurePath', 'PurePosixPath', 'fspath', 'abspath', 'realpath', 'normpath',
            'expanduser'}
NO_CONTENT = {'exists', 'is_dir', 'is_file', 'isdir', 'isfile', 'mkdir', 'makedirs', 'is_symlink', 'rmtree',
              'samefile'}
INCLUDE_FLAGS = {'-I', '-isystem', '-iquote', '-idirafter'}
LIBRARY_LOADERS = {'CDLL', 'PyDLL', 'LoadLibrary', 'load_library', 'dlopen'}
MAX_VALUES = 256
MAX_PATTERN_TARGETS = 8   # a computed path naming more targets than this stands for its whole make directory
SEP = '\x1f'
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


@_memo
def _py_index(root: Path) -> dict[str, tuple[Path, ...]]:
    """Repository Python files by module name (tracked and untracked; for imports no search path resolves)."""
    done = subprocess.run(['git', '-C', str(root), 'ls-files', '-co', '--exclude-standard', '*.py'],
                          capture_output=True, text=True)
    index: dict[str, list[Path]] = {}
    for line in done.stdout.splitlines():
        if not line.startswith('tools/'):
            index.setdefault(PurePosixPath(line).stem, []).append(root / line)
    return {k: tuple(v) for k, v in index.items()}


def _strings(values) -> set[str] | None:
    """The plain-string members of a folded value set (None when unknown)."""
    if values is None:
        return None
    return {v[2:] for v in values if v.startswith('S:')}


def _norm(path: str) -> str | None:
    path = os.path.normpath(path.lstrip('/')) if path else ''
    if path == '.':
        return ''
    return None if path.startswith('..') else path


def _sym(key: str, head: str = 'S:', tail: str = '') -> str:
    return f'A:{key}{SEP}{head}{SEP}{tail}'


def _unsym(value: str) -> tuple[str, str, str]:
    key, head, tail = value[2:].split(SEP)
    return key, head, tail


def _concat(left: str, right: str) -> str | None:
    """String concatenation of two values (f-strings, +)."""
    lk, rk = left[:2], right[:2]
    if lk == 'S:' and rk == 'S:':
        return 'S:' + left[2:] + right[2:]
    if lk == 'P:' and rk == 'S:':
        return 'P:' + (left[2:] + right[2:] if left[2:] else right[2:].lstrip('/'))
    if lk == 'S:' and rk == 'P:':
        return right if not left[2:] else None
    if lk == 'A:' and rk == 'S:':
        key, head, tail = _unsym(left)
        return _sym(key, head, tail + right[2:])
    if lk in ('S:', 'P:') and rk == 'A:':
        key, head, tail = _unsym(right)
        if head[:2] != 'S:':
            return None if left[2:] else right
        if lk == 'P:':
            return _sym(key, 'P:' + (left[2:] + head[2:] if left[2:] else head[2:].lstrip('/')), tail)
        return _sym(key, 'S:' + left[2:] + head[2:], tail)
    return None


def _join(left: str, right: str) -> str | None:
    """Path join (``/``, os.path.join) of two values."""
    if right.startswith('P:'):
        return right
    if right.startswith('A:'):
        key, head, tail = _unsym(right)
        if head[:2] == 'P:':
            return right
        if left.startswith('A:'):
            return None
        return _sym(key, left[:2] + (left[2:] + '/' if left[2:] else '') + head[2:], tail)
    text = right[2:]
    if text.startswith('/'):
        return None
    if left.startswith('A:'):
        key, head, tail = _unsym(left)
        return _sym(key, head, f'{tail}/{text}')
    joined = f'{left[2:]}/{text}' if left[2:] else text
    if left.startswith('P:'):
        normed = _norm(joined)
        return None if normed is None else 'P:' + normed
    return 'S:' + joined


def _dirname(value: str) -> str | None:
    if value.startswith('P:'):
        return 'P:' + os.path.dirname(value[2:]) if value[2:] else None
    if value.startswith('A:'):
        key, head, tail = _unsym(value)
        return _sym(key, head, tail.rsplit('/', 1)[0]) if '/' in tail else None
    return None


def _instantiate(value: str, argument: str) -> str | None:
    """A parameter's value (A:) with the argument a call passes for it."""
    key, head, tail = _unsym(value)
    if argument.startswith('A:'):
        akey, ahead, atail = _unsym(argument)
        if head == 'S:':
            return _sym(akey, ahead, atail + tail)
        if ahead == 'S:' and not atail:
            return _sym(akey, head, tail)
        return None
    middle = _concat(head, argument) if head != 'S:' else argument
    if middle is None:
        return None
    if middle.startswith('P:') and tail:
        normed = _norm(middle[2:] + tail if middle[2:] else tail)
        return None if normed is None else 'P:' + normed
    return middle[:2] + middle[2:] + tail if tail else middle


class _Sink:
    """What a module (or a resolved parameter use) contributes to a closure."""

    def __init__(self):
        self.deps = Deps()
        self.imports: list[tuple[str, Path]] = []        # (module name, importing file)
        self.py_files: list[str] = []
        self.search: set[str] = set()
        self.make_uses: set[tuple[str, str | None]] = set()
        self.include_dirs: set[str] = set()


class _Module:
    """Static facts of one Python file: its imports, the repository paths its code builds and how, and the
    uses of its functions' parameters (resolved later at the call sites)."""

    def __init__(self, path: Path, root: Path):
        self.path, self.root = path, root
        self.me = rel(path, root)
        self.near = rel(path.parent, root) or ''
        self.sink = _Sink()
        self.c_includes: set[str] = set()
        self.functions: dict[str, list] = {}       # name -> FunctionDef nodes
        self.aliases: dict[str, str] = {}          # local name -> imported module name
        self.from_names: dict[str, tuple[str, str]] = {}   # local name -> (module, attribute)
        self.param_uses: list[tuple] = []   # (A: value, context, line, in mutant-only code)
        self.deferred: list[tuple] = []     # (value, callee ref, line, in mutant-only code): a call argument
        self.calls: list[tuple[tuple, list, dict]] = []   # (callee ref, positional values, keyword values)
        self.referenced: set[str] = set()          # local functions used as values (callbacks)
        # TEST-SPEED-005: code that runs only as a script (inside a module-level main() or under
        # `if __name__ == '__main__':`). For an imported module whose main() the closure never calls, its path
        # uses, call sites and symbol names are not inputs.
        self.main_region: set[int] = set()
        self.mutant_region: set[int] = set()       # code that runs only for mutants (see _regions)
        self.mutant_sink = _Sink()
        self.main_sink = _Sink()
        self.main_mutant_sink = _Sink()
        self.main_param_uses: list[tuple] = []
        self.main_deferred: list[tuple] = []
        self.main_calls: list[tuple[tuple, list, dict]] = []
        self.main_refs: set[str] = set()           # imported module names whose .main this file uses
        self.own_main_used = False                 # this file calls/uses its own main() outside the guard
        try:
            text = path.read_text(errors='replace')
        except OSError:
            return
        try:
            self.tree = ast.parse(text)
        except SyntaxError:
            self.sink.deps.fallback[self.me] = f'{self.me} does not parse'
            self.sink.deps.sym_dynamic[self.me] = f'{self.me} does not parse'
            self.sink.deps.words |= set(re.findall(r"""['"]([^'"\n]{1,200})['"]""", text))
            return
        self.nodes = list(ast.walk(self.tree))
        self.parents = {child: node for node in self.nodes for child in ast.iter_child_nodes(node)}
        self.assigned: dict[str, list] = {}
        for node in self.nodes:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                self.assigned.setdefault(node.targets[0].id, []).append(node.value)
        self._scopes: dict = {}
        for node in self.nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions.setdefault(node.name, []).append(node)
        self._main_region()
        self._imports()
        self._bind()
        self._loaders()
        self._constants()
        self._visit(self.tree)
        self._call_sites()
        self._symbols()

    # -- scopes and values -------------------------------------------------------------------
    def scope(self, node):
        """The innermost function enclosing NODE (None: the module)."""
        if node in self._scopes:
            return self._scopes[node]
        parent = self.parents.get(node)
        while parent is not None and not isinstance(parent, SCOPES):
            parent = self.parents.get(parent)
        self._scopes[node] = parent
        return parent

    def lookup(self, name: str, node):
        scope = self.scope(node)
        while True:
            if (scope, name) in self.env:
                return self.env[(scope, name)], True
            if scope is None:
                return None, False
            scope = self.scope(scope)

    def key(self, fn, param: str) -> str:
        return f'{self.me}::{fn.name}::{param}'

    def fold(self, node, depth=0):
        """A frozenset of values (see above), or None when unknown."""
        if depth > 40:
            return None
        f = functools.partial(self.fold, depth=depth + 1)
        if isinstance(node, ast.Constant):
            return frozenset({'S:' + node.value}) if isinstance(node.value, str) else None
        if isinstance(node, ast.Name):
            value, bound = self.lookup(node.id, node)
            if bound:
                return value
            if node.id in ROOT_NAMES:
                return frozenset({'P:'})
            if node.id == '__file__':
                return frozenset({'P:' + self.me})
            return None
        if isinstance(node, ast.Attribute):
            if node.attr in ROOT_NAMES:
                return frozenset({'P:'})
            if node.attr == 'parent':
                return self._map(f(node.value), _dirname)
            return None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and \
                node.value.attr == 'parents' and isinstance(node.slice, ast.Constant) and \
                isinstance(node.slice.value, int):
            inner = f(node.value.value)
            for _ in range(node.slice.value + 1):
                inner = self._map(inner, _dirname)
            return inner
        if isinstance(node, ast.IfExp):
            body, orelse = f(node.body), f(node.orelse)
            if body is None and orelse is None:
                return None
            return self._cap((body or frozenset({'S:*'})) | (orelse or frozenset({'S:*'})))
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            values = [f(v) for v in node.values]
            return None if any(v is None for v in values) else self._cap(frozenset().union(*values))
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if isinstance(node.func, ast.Attribute) and name in ('resolve', 'absolute', 'expanduser') and \
                    not node.args:
                return f(node.func.value)
            if name in WRAPPERS and len(node.args) == 1 and not node.keywords:
                return f(node.args[0])
            if name == 'dirname' and len(node.args) == 1:
                return self._map(f(node.args[0]), _dirname)
            if name == 'join' and isinstance(node.func, ast.Attribute) and _call_name(node.func.value) == 'path':
                return self._join_all([f(a) for a in node.args])
            if name == 'joinpath' and isinstance(node.func, ast.Attribute):
                return self._join_all([f(node.func.value)] + [f(a) for a in node.args])
            if name == 'with_suffix' and isinstance(node.func, ast.Attribute) and len(node.args) == 1:
                base, suffixes = f(node.func.value), _strings(f(node.args[0]))
                if base is None or suffixes is None:
                    return None
                return self._cap(frozenset(v[:2] + os.path.splitext(v[2:])[0] + s
                                           for v in base if v[:2] in ('S:', 'P:') for s in suffixes)) or None
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self._join_all([f(node.left), f(node.right)])
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = f(node.left), f(node.right)
            if left is None and right is None:
                return None
            return self._concat_all([left or frozenset({'S:*'}), right or frozenset({'S:*'})])
        if isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                if isinstance(part, ast.Constant):
                    parts.append(frozenset({'S:' + str(part.value)}))
                elif isinstance(part, ast.FormattedValue) and part.format_spec is None:
                    value = f(part.value)
                    parts.append(value if value is not None else frozenset({'S:*'}))
                else:
                    parts.append(frozenset({'S:*'}))
            return self._concat_all(parts)
        return None

    def _join_all(self, parts):
        if not parts or parts[0] is None:
            # an unknown base joined with a literal repository path ('Path(repo) / "scripts/x.py"')
            if len(parts) == 2 and parts[1] is not None:
                found = frozenset('P:' + p for v in parts[1] for p in [self._resolve(v)] if p)
                return found or None
            return None
        acc = parts[0]
        for part in parts[1:]:
            if part is None:
                part = frozenset({'S:*'})
            acc = frozenset(j for a in acc for b in part for j in [_join(a, b)] if j is not None)
            if not acc or len(acc) > MAX_VALUES:
                return None
        return acc

    def _concat_all(self, parts):
        if any(p is None for p in parts):
            return None
        acc = frozenset({'S:'})
        for part in parts:
            acc = frozenset(j for a in acc for b in part for j in [_concat(a, b)] if j is not None)
            if not acc or len(acc) > MAX_VALUES:
                return None
        return acc

    @staticmethod
    def _map(values, fn):
        if values is None:
            return None
        out = frozenset(r for v in values for r in [fn(v)] if r is not None)
        return out or None

    @staticmethod
    def _cap(values):
        return values if values is not None and len(values) <= MAX_VALUES else None

    # -- bindings ----------------------------------------------------------------------------
    def _bind(self):
        """Flow-insensitive values of every simply bound name, per function scope: assignments and loops over
        constant tuples; a parameter is symbolic (A:). A name bound any other way is unknown."""
        binds: dict[tuple, list] = {}
        unknown: set[tuple] = set()
        params: dict[tuple, frozenset] = {}
        declared_global: dict = {}
        for node in self.nodes:
            if isinstance(node, ast.Global):
                declared_global.setdefault(self.scope(node), set()).update(node.names)

        def where(node, name):
            scope = self.scope(node)
            return (None, name) if name in declared_global.get(scope, ()) else (scope, name)

        for node in self.nodes:
            if isinstance(node, SCOPES):
                args = node.args
                for arg in args.posonlyargs + args.args + args.kwonlyargs + \
                        [a for a in (args.vararg, args.kwarg) if a is not None]:
                    if isinstance(node, ast.Lambda) or arg in (args.vararg, args.kwarg):
                        unknown.add((node, arg.arg))
                    else:
                        params[(node, arg.arg)] = frozenset({_sym(self.key(node, arg.arg))})
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    self._bind_target(target, node.value, binds, unknown, where)
            elif isinstance(node, ast.NamedExpr):
                binds.setdefault(where(node, node.target.id), []).append(node.value)
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
                self._bind_loop(node, binds, unknown, where)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                unknown.add(where(node, node.target.id))
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    for name in _names(item.optional_vars):
                        unknown.add(where(node, name))
            elif isinstance(node, ast.ExceptHandler) and node.name:
                unknown.add(where(node, node.name))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    unknown.add(where(node, (alias.asname or alias.name).split('.')[0]))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                pass
        self.env: dict[tuple, frozenset | None] = dict(params)
        for key in unknown:
            self.env[key] = None
        for _ in range(5):
            changed = False
            for key, exprs in binds.items():
                if key in unknown:
                    continue
                values: set | None = set()
                for expr in exprs:
                    value = self.fold(expr)
                    if value is None:
                        values = None
                        break
                    values |= value
                new = self._cap(frozenset(values)) if values is not None else None
                if self.env.get(key, 'missing') != new:
                    self.env[key] = new
                    changed = True
            if not changed:
                break

    def _bind_target(self, target, value, binds, unknown, where):
        if isinstance(target, ast.Name):
            binds.setdefault(where(target, target.id), []).append(value)
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)) and \
                len(target.elts) == len(value.elts):
            for t, v in zip(target.elts, value.elts):
                self._bind_target(t, v, binds, unknown, where)
        else:
            for name in _names(target):
                unknown.add(where(target, name))

    def _bind_loop(self, node, binds, unknown, where):
        target, iterable = node.target, node.iter
        elements = None
        if isinstance(iterable, (ast.Tuple, ast.List, ast.Set)):
            elements = iterable.elts
        elif isinstance(iterable, ast.Name):
            assigned = self._single_assign(iterable.id)
            if isinstance(assigned, (ast.Tuple, ast.List, ast.Set)):
                elements = assigned.elts
        if elements is None or any(isinstance(e, ast.Starred) for e in elements):
            for name in _names(target):
                unknown.add(where(target, name))
            return
        if isinstance(target, ast.Name):
            binds.setdefault(where(target, target.id), []).extend(elements)
        elif isinstance(target, ast.Tuple) and all(isinstance(t, ast.Name) for t in target.elts) and \
                all(isinstance(e, (ast.Tuple, ast.List)) and len(e.elts) == len(target.elts) for e in elements):
            for i, t in enumerate(target.elts):
                binds.setdefault(where(t, t.id), []).extend(e.elts[i] for e in elements)
        else:
            for name in _names(target):
                unknown.add(where(target, name))

    def _single_assign(self, name):
        found = self.assigned.get(name, [])
        return found[0] if len(found) == 1 else None

    # -- imports, loaders and constants ------------------------------------------------------
    def _imports(self):
        for node in self.nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.sink.imports.append((alias.name, self.path))
                    if alias.asname:
                        self.aliases[alias.asname] = alias.name
                    else:
                        self.aliases[alias.name.split('.')[0]] = alias.name.split('.')[0]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                self.sink.imports.append((node.module, self.path))
                for alias in node.names:
                    self.sink.imports.append((f'{node.module}.{alias.name}', self.path))
                    self.from_names[alias.asname or alias.name] = (node.module, alias.name)
            elif isinstance(node, ast.ImportFrom) and node.level:
                for alias in node.names:
                    self.sink.imports.append((alias.name, self.path))
                if node.module:
                    self.sink.imports.append((node.module, self.path))
                    for alias in node.names:
                        self.from_names[alias.asname or alias.name] = (node.module, alias.name)

    def _loaders(self):
        for node in self.nodes:
            if isinstance(node, ast.Call) and _call_name(node.func) in LOADERS:
                index = LOADERS[_call_name(node.func)]
                if len(node.args) <= index:
                    continue
                values = self.fold(node.args[index])
                where = f'{self.me}:{node.lineno}'
                if values is None:
                    self.sink.deps.fallback[where] = f'{where} loads a module from a computed name'
                    continue
                for value in values:
                    if value.startswith('A:'):
                        self.param_uses.append((value, ('loader',), where, False))
                    else:
                        self.apply(self.sink, value, ('loader', where), where)

    def _constants(self):
        for node in self.nodes:
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                self.c_includes.update(INCLUDE.findall(text))
                if 2 < len(text) < 80 and not text.isspace() and '\n' not in text:
                    self.sink.deps.words.add(text)
                    base = text.rsplit('/', 1)[-1]
                    if FILE_NAME.fullmatch(base) and not text.startswith('/') and '{' not in text:
                        self.sink_for(node).deps.names.setdefault(text if '/' in text else base, f'{self.me} quotes {text!r}')

    def _resolve(self, value: str) -> str | None:
        """A concrete value as a repository path: 'P:' values as they are, plain strings that name an existing
        path relative to the repository or to this file's directory."""
        if value.startswith('P:'):
            return _norm(value[2:])
        if not value.startswith('S:'):
            return None
        text = value[2:].strip()
        if '/' not in text or text.startswith(('/', 'http:', 'https:')) or '{' in text or '\n' in text \
                or '*' in text or ' ' in text:
            return None
        text = text.rstrip('/')
        for base in ('', self.near):
            candidate = _norm(os.path.join(base, text) if base else text)
            if candidate and (self.root / candidate).exists():
                return candidate
        return None

    # -- path uses ---------------------------------------------------------------------------
    PATHY = (ast.Constant, ast.Name, ast.Attribute, ast.Subscript, ast.Call, ast.BinOp, ast.JoinedStr,
             ast.IfExp, ast.BoolOp)

    def _visit(self, node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, self.PATHY) and not (isinstance(child, (ast.Name, ast.Attribute, ast.Subscript))
                                                       and not isinstance(child.ctx, ast.Load)):
                values = self.fold(child)
                concrete = {v for v in values or () if not v.startswith('A:') and self._resolve(v) is not None}
                symbolic = {v for v in values or () if v.startswith('A:')}
                if concrete or symbolic:
                    context = self._context(child)
                    line = f'{self.me}:{getattr(child, "lineno", "?")}'
                    main = id(child) in self.main_region
                    sink = self.sink_for(child)
                    for value in sorted(concrete | symbolic):
                        if context[0] == 'callarg':
                            (self.main_deferred if main else self.deferred).append(
                                (value, context[1], line, id(child) in self.mutant_region))
                        elif value.startswith('A:'):
                            (self.main_param_uses if main else self.param_uses).append(
                                (value, context, line, id(child) in self.mutant_region))
                        else:
                            self.apply(sink, value, context, line)
                    continue
            self._visit(child)

    def apply(self, sink: _Sink, value: str, context: tuple, line: str) -> None:
        """Record a concrete value used in CONTEXT."""
        if context[0] == 'loader':
            if value.startswith('S:') and '/' not in value and not value.endswith('.py') and '*' not in value:
                sink.imports.append((value[2:], self.path))
                return
            path = self._resolve(value)
            if path is None or '*' in (path or '') or not (self.root / path).is_file():
                sink.deps.fallback[line] = f'{line} loads a module from a computed name ({value[2:]})'
                return
            sink.py_files.append(path)
            sink.deps.files.setdefault(path, f'{self.me} loads {path}')
            return
        path = self._resolve(value)
        if path is None:
            return
        full = self.root / path if path else self.root
        if '*' in path:
            self._pattern(sink, path, line)
        elif path == '':
            return
        elif full.is_file():
            sink.deps.files.setdefault(path, f'{self.me} names {path}')
            if full.suffix == '.py':
                sink.py_files.append(path)
            self._target(sink, path)
        elif full.is_dir():
            self._directory(sink, path, context, line)
        else:
            self._target(sink, path)

    def _pattern(self, sink: _Sink, pattern: str, line: str):
        """A path built from a value the analysis cannot know: every file it can match (fnmatch '*' also
        crosses '/'), and the make targets it can name. A computed name at the repository root or a computed
        Python module cannot be bounded: fallback."""
        head = pattern.split('*', 1)[0]
        directory = head.rsplit('/', 1)[0] if '/' in head else ''
        if not directory:
            sink.deps.fallback[line] = f'{line} builds a repository path from a computed name ({pattern})'
            return
        if pattern.endswith('.py') or (pattern == directory + '/*' and directory in SEARCH_DIRS):
            sink.deps.fallback[line] = f'{line} builds a Python path from a computed name ({pattern})'
            return
        sink.deps.globs.setdefault(pattern, f'{line} builds {pattern}')
        if (self.root / directory / 'Makefile').is_file():
            rest = pattern[len(directory) + 1:]
            targets = [t for t in make_targets(directory, self.root) if fnmatch.fnmatchcase(t, rest)]
            if len(targets) > MAX_PATTERN_TARGETS:   # 'build/*': any target there, i.e. the whole directory
                sink.deps.update(makefile_deps(directory, self.root))
            else:
                sink.make_uses.update((directory, t) for t in targets)

    def _target(self, sink: _Sink, path: str):
        """A path inside a make directory that is one of its targets (built or not): that target's inputs."""
        parts = PurePosixPath(path).parts
        for i in range(len(parts) - 1, 0, -1):
            directory = '/'.join(parts[:i])
            if (self.root / directory / 'Makefile').is_file():
                rest = '/'.join(parts[i:])
                if rest in make_targets(directory, self.root):
                    sink.make_uses.add((directory, rest))
                return

    def _directory(self, sink: _Sink, path: str, context, line: str):
        kind = context[0]
        if kind in ('none', 'bound') or (path in SEARCH_DIRS and kind == 'whole'):
            return
        if kind == 'search':
            sink.search.add(path)
        elif kind == 'include':
            sink.include_dirs.add(path)
        elif kind == 'glob' and context[1] is not None:
            for pattern in context[1]:
                sink.deps.globs.setdefault(f'{path}/{pattern}', f'{line} globs {path}/{pattern}')
        elif kind == 'make' and context[1] is not None:
            for target in context[1] or [None]:
                if target != '':
                    sink.make_uses.add((path, target))
        elif kind == 'library' and (self.root / path / 'Makefile').is_file():
            libraries = [t for t in make_targets(path, self.root) if t.endswith(('.dylib', '.so')) and '%' not in t]
            if 0 < len(libraries) <= MAX_PATTERN_TARGETS:
                sink.make_uses.update((path, t) for t in libraries)
            else:
                sink.deps.update(makefile_deps(path, self.root))
        elif kind == 'target':
            sink.deps.dirs.setdefault(path, f'{line} names {path}/')
            sink.deps.built_dirs.add(path)
        else:
            # every file below, but unit tests and docs (never read by a validator through a directory)
            sink.deps.dirs.setdefault(path, f'{line} names {path}/')
            sink.deps.built_dirs.add(path)

    def _context(self, node) -> tuple:
        """How a path-valued expression is used: ('include',) ('search',) ('none',) ('bound',)
        ('glob', patterns) ('make', targets) or ('whole',)."""
        parent = self.parents.get(node)
        if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div) and parent.left is node:
            outer = parent   # D / <unknown> ... handed to a library loader: a library D builds
            while True:
                up = self.parents.get(outer)
                if isinstance(up, ast.BinOp) and isinstance(up.op, ast.Div) and up.left is outer or \
                        isinstance(up, ast.Call) and _call_name(up.func) in WRAPPERS and up.args and up.args[0] is outer:
                    outer = up
                    continue
                break
            if isinstance(up, ast.Call) and _call_name(up.func) in LIBRARY_LOADERS and up.args and up.args[0] is outer:
                return ('library',)
        if isinstance(parent, ast.Attribute) and parent.value is node:
            call = self.parents.get(parent)
            if parent.attr in ('glob', 'rglob') and isinstance(call, ast.Call) and call.func is parent and call.args:
                patterns = _strings(self.fold(call.args[0]))
                if not patterns:
                    return ('glob', None)
                return ('glob', tuple(sorted(('**/' if parent.attr == 'rglob' else '') + p for p in patterns)))
            if parent.attr in NO_CONTENT:
                return ('none',)
            if parent.attr == 'relative_to':
                return ('target',)   # make -C D <path relative to D>: the path is the target
            return ('whole',)
        if isinstance(parent, (ast.List, ast.Tuple)):
            index = next(i for i, e in enumerate(parent.elts) if e is node)
            previous = _strings(self.fold(parent.elts[index - 1])) if index else set()
            if previous and previous & INCLUDE_FLAGS:
                return ('include',)
            if previous and '-C' in previous and 'make' in (_strings(self.fold(parent.elts[0])) or ()):
                return self._make_targets(parent.elts[index + 1:])
            holder = self.parents.get(parent)
            if isinstance(holder, (ast.For, ast.AsyncFor, ast.comprehension)) and holder.iter is parent and \
                    all(self.lookup(n, holder.target)[0] is not None for n in _names(holder.target)):
                return ('bound',)
            if isinstance(holder, ast.Assign) and self._assigned_known(holder):
                return ('bound',)
            return ('whole',)
        if isinstance(parent, ast.keyword):
            call = self.parents.get(parent)
            if parent.arg == 'cwd' and isinstance(call, ast.Call) and call.args and \
                    isinstance(call.args[0], (ast.List, ast.Tuple)) and call.args[0].elts and \
                    'make' in (_strings(self.fold(call.args[0].elts[0])) or ()):
                return self._make_targets(call.args[0].elts[1:])
            if isinstance(call, ast.Call) and self.callee(call.func) is not None:
                return ('callarg', self.callee(call.func))
            return ('whole',)
        if isinstance(parent, ast.Call) and node in parent.args:
            name = _call_name(parent.func)
            if name in ('insert', 'append') and isinstance(parent.func, ast.Attribute) and \
                    _call_name(parent.func.value) == 'path':
                return ('search',)
            if name in NO_CONTENT or name == 'relative_to':
                return ('none',)
            if self.callee(parent.func) is not None:
                return ('callarg', self.callee(parent.func))
            return ('whole',)
        if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Add) and parent.right is node and \
                (_strings(self.fold(parent.left)) or set()) & INCLUDE_FLAGS:
            return ('include',)
        if isinstance(parent, ast.FormattedValue):
            text = self.parents.get(parent)
            if isinstance(text, ast.JoinedStr):
                index = next(i for i, v in enumerate(text.values) if v is parent)
                before = text.values[index - 1] if index else None
                if isinstance(before, ast.Constant) and isinstance(before.value, str) and \
                        before.value.rstrip().endswith(tuple(INCLUDE_FLAGS)):
                    return ('include',)
            return ('whole',)
        if isinstance(parent, (ast.Assign, ast.AnnAssign)) and parent.value is node and self._assigned_known(parent):
            return ('bound',)
        if isinstance(parent, ast.NamedExpr) and self.lookup(parent.target.id, parent)[0] is not None:
            return ('bound',)
        if isinstance(parent, ast.Compare):
            return ('none',)
        if isinstance(parent, ast.Return):
            return ('return',)
        return ('whole',)

    def _make_targets(self, elements) -> tuple:
        targets = []
        for element in elements:
            inner = element.args[0] if isinstance(element, ast.Call) and _call_name(element.func) == 'str' and \
                element.args else element
            if isinstance(inner, ast.Call) and _call_name(inner.func) == 'relative_to':
                targets.append('')   # the path the target is relative to is its own use ('target')
                continue
            values = _strings(self.fold(element))
            if values is None:
                return ('make', None)   # a computed target: the whole directory
            targets += [v for v in values if not v.startswith('-') and '=' not in v]
        return ('make', tuple(sorted(targets)))

    def _assigned_known(self, node) -> bool:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [n for t in targets for n in _names(t)]
        return bool(names) and all(isinstance(t, (ast.Name, ast.Tuple, ast.List)) for t in targets) and \
            all(self.lookup(n, t)[0] is not None for t in targets for n in _names(t))

    # -- calls -------------------------------------------------------------------------------
    def callee(self, func) -> tuple[str, str] | None:
        """(module name or '' for this file, function) for a call of a local function or a function of an
        imported module, or None."""
        if isinstance(func, ast.Name):
            if func.id in self.functions:
                return ('', func.id)
            if func.id in self.from_names:
                return self.from_names[func.id]
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in self.aliases:
            return (self.aliases[func.value.id], func.attr)
        return None

    def _call_sites(self):
        for node in self.nodes:
            if isinstance(node, ast.Call):
                ref = self.callee(node.func)
                if ref is None:
                    continue
                calls = self.main_calls if id(node) in self.main_region else self.calls
                if any(isinstance(a, ast.Starred) for a in node.args) or any(k.arg is None for k in node.keywords):
                    calls.append((ref, None, None))
                    continue
                calls.append((ref, [self.fold(a) for a in node.args],
                              {k.arg: self.fold(k.value) for k in node.keywords}))
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in self.functions:
                parent = self.parents.get(node)
                if not (isinstance(parent, ast.Call) and parent.func is node):
                    self.referenced.add(node.id)

    # -- main()-only code, mutant-only code and symbol names (TEST-SPEED-005) ------------------
    def sink_for(self, node) -> _Sink:
        main, mutant = id(node) in self.main_region, id(node) in self.mutant_region
        return (self.main_mutant_sink if mutant else self.main_sink) if main else \
            (self.mutant_sink if mutant else self.sink)

    def _main_region(self):
        for node in self.nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and MUTANT_WORD.search(node.name) or \
                    isinstance(node, ast.If) and _mutant_test(node.test):
                body = [node] if not isinstance(node, ast.If) else node.body
                for part in body:
                    self.mutant_region |= {id(n) for n in ast.walk(part)}
        for statement in self.tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) and statement.name == 'main':
                self.main_region |= {id(n) for n in ast.walk(statement)}
            elif isinstance(statement, ast.If) and _is_main_guard(statement.test):
                for part in statement.body:
                    self.main_region |= {id(n) for n in ast.walk(part)}

    def _symbols(self):
        """The names this file can use from a loaded C library: every identifier and attribute, every word
        of a string constant, the names its string-building expressions can produce (regex patterns), and
        the places where a name given to getattr/hasattr/in_dll cannot be bounded."""
        for local, (module, attribute) in self.from_names.items():
            if attribute == 'main':
                self.main_refs.add(module)
        for node in self.nodes:
            if id(node) not in self.main_region:
                if isinstance(node, ast.Name) and node.id == 'main' and isinstance(node.ctx, ast.Load) and \
                        'main' in self.functions:
                    self.own_main_used = True
                elif isinstance(node, ast.Attribute) and node.attr == 'main' and \
                        isinstance(node.value, ast.Name) and node.value.id in self.aliases:
                    self.main_refs.add(self.aliases[node.value.id])
            deps = (self.main_sink if id(node) in self.main_region else self.sink).deps
            if isinstance(node, ast.Attribute):
                deps.symbols.add(node.attr)
            elif isinstance(node, ast.Name):
                deps.symbols.add(node.id)
            elif isinstance(node, ast.keyword) and node.arg:
                deps.symbols.add(node.arg)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                deps.symbols.update(IDENT.findall(node.value))
            elif isinstance(node, ast.Constant) and isinstance(node.value, bytes):
                deps.symbols.update(IDENT.findall(node.value.decode('latin-1')))
            where = f'{self.me}:{getattr(node, "lineno", "?")}'
            if _builds_string(node) and not _builds_string(self.parents.get(node)):
                for text in self._built_names(node):
                    if '*' not in text:
                        deps.symbols.update(IDENT.findall(text))
                    elif _name_pattern(text):
                        deps.sym_patterns.setdefault(_name_pattern(text), where)
            # A lookup by a plain variable takes a name the program holds as a string (counted above, at the
            # constant or at the expression that built it) or reads from data (not visible, like data paths).
            # A name built right in the lookup from parts that cannot be bounded is the fallback.
            if isinstance(node, ast.Call) and _call_name(node.func) in SYMBOL_LOOKUPS and len(node.args) >= 2 and \
                    isinstance(node.args[1], (ast.BinOp, ast.JoinedStr, ast.Call)):
                texts = self._built_names(node.args[1])
                if not texts or any('*' in t and not _name_pattern(t) for t in texts):
                    deps.sym_dynamic.setdefault(where, f'{where} looks up a symbol name it cannot bound')
                for text in texts:
                    if '*' not in text:
                        deps.symbols.update(IDENT.findall(text))
                    elif _name_pattern(text):
                        deps.sym_patterns.setdefault(_name_pattern(text), where)

    def _built_names(self, node) -> list[str]:
        """The strings NODE can evaluate to, '*' marking unknown parts ([] when nothing is known)."""
        values = self.fold(node)
        if values is not None:
            out = []
            for value in values:
                if value.startswith('S:'):
                    out.append(value[2:])
                elif value.startswith('A:'):
                    _, head, tail = _unsym(value)
                    out.append((head[2:] if head.startswith('S:') else '') + '*' + tail)
                else:
                    out.append('*')
            return out
        text = _template(node)
        return [text] if text is not None else []


MUTANT_WORD = re.compile(r'mutant|mutation', re.I)


def _mutant_test(test) -> bool:
    """An `if` that runs only when mutants are requested: `if args.mutations:`, `if mutants and ...`."""
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return any(_mutant_test(v) for v in test.values)
    if isinstance(test, (ast.Name, ast.Attribute)):
        return bool(MUTANT_WORD.search(test.id if isinstance(test, ast.Name) else test.attr))
    return False


def _is_main_guard(test) -> bool:
    """`__name__ == '__main__'` (either order)."""
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
        return False
    sides = [test.left, test.comparators[0]]
    return any(isinstance(x, ast.Name) and x.id == '__name__' for x in sides) and \
        any(isinstance(x, ast.Constant) and x.value == '__main__' for x in sides)


IDENT = re.compile(r'[A-Za-z_]\w*')
SYMBOL_LOOKUPS = {'getattr', 'hasattr', 'in_dll', 'dlsym'}


def _builds_string(node) -> bool:
    """An f-string, a '+'/'%' expression or a .format call with a constant string part."""
    if not isinstance(node, (ast.JoinedStr, ast.BinOp, ast.Call)) or \
            (isinstance(node, ast.BinOp) and not isinstance(node.op, (ast.Add, ast.Mod))):
        return False
    text = _template(node)
    return text is not None and bool(text.strip('*')) and \
        (not isinstance(node, ast.Call) or _call_name(node.func) == 'format')


def _template(node) -> str | None:
    """A string expression with '*' for every part not known statically (None: not a string expression)."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        return ''.join(v.value if isinstance(v, ast.Constant) else '*' for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _template(node.left), _template(node.right)
        if left is None and right is None:
            return None
        return (left if left is not None else '*') + (right if right is not None else '*')
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant) and \
            isinstance(node.left.value, str):
        return re.sub(r'%[-#0 +]*\d*(?:\.\d+)?[sdirxXfgeEc]', '*', node.left.value)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'format' and \
            isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str):
        return re.sub(r'\{[^{}]*\}', '*', node.func.value.value)
    return '*'


def _name_pattern(text: str) -> str | None:
    """TEXT ('*' unknown) as a template of C symbol names, or None if TEXT cannot be one or is only unknown
    (no constant identifier part of 3+ characters)."""
    if '*' not in text or not IDENT.fullmatch(text.replace('*', 'x')) or \
            not re.search(r'[A-Za-z_0-9]{3}', text.replace('*', ' ')):
        return None
    return re.sub(r'\*+', '*', text)


def fragments(symbols: set[str]) -> frozenset[str]:
    """The lower-case word pieces of a unit's names and string words (split at '_' and digits)."""
    return frozenset(piece.lower() for token in symbols for piece in re.split(r'[_\d]+', token) if piece)


def template_matches(template: str, name: str, pieces: frozenset[str]) -> bool:
    """Can NAME come from TEMPLATE when every '*' is filled with the program's own strings: a run of word
    pieces (PIECES, any case), underscores and digits? (A name assembled at run time from strings the code
    holds; a name read from a data file is not visible, like a path read from one.)"""
    parts = re.split(r'(\*)', template)
    lower = name.lower()

    @functools.lru_cache(maxsize=None)
    def words(i: int, j: int) -> bool:   # lower[i:j] is pieces / '_' / digits only
        if i == j:
            return True
        if lower[i] == '_' or lower[i].isdigit():
            return words(i + 1, j)
        return any(lower[i:k] in pieces and words(k, j) for k in range(i + 1, j + 1))

    @functools.lru_cache(maxsize=None)
    def match(p: int, i: int) -> bool:
        if p == len(parts):
            return i == len(name)
        part = parts[p]
        if part == '*':
            return any(words(i, k) and match(p + 1, k) for k in range(i, len(name) + 1))
        return name.startswith(part, i) and match(p + 1, i + len(part))
    return match(0, 0)


def _call_name(func) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _names(target) -> list[str]:
    """The names a binding target stores (not the names read inside ``a[i] = ...`` or ``a.b = ...``)."""
    if target is None:
        return []
    return [n.id for n in ast.walk(target) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)]


@_memo
def _module(path: Path, root: Path) -> _Module:
    return _Module(path, root)


def _module_file(name: str, near: Path, root: Path, extra: tuple[str, ...] = ()) -> Path | None:
    parts = name.split('.')
    for base in (near, root / 'scripts', root / 'native/tests', *(root / d for d in extra)):
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


@_memo
def _closure(path: Path, root: Path, tooling: bool) -> Deps:
    """The inputs of a Python program starting at PATH (see python_deps)."""
    me = rel(path, root)
    out = Deps()
    if me is None or not path.is_file():
        return out
    out.files[me] = f'is {me}'
    modules: dict[Path, _Module] = {}
    queue: list[tuple[Path, str | None]] = [(path, None)]
    seen = {path}
    sinks: list[_Sink] = []
    resolved = _Sink()
    resolved_mutant = _Sink()

    def enqueue(module: Path, via: str):
        name = rel(module, root)
        if module in seen or name is None or (name in TOOLING and (
                not tooling or (tooling == 'direct' and via != me))):
            return
        seen.add(module)
        queue.append((module, via))

    def search_dirs():
        return tuple(sorted(set().union(*(s.search for s in sinks), resolved.search)))

    def resolve_import(module_name: str, importer: Path, via: str, final: bool):
        module = _module_file(module_name, importer.parent, root, search_dirs())
        if module is not None:
            enqueue(module, via)
            return True
        if not final:
            return False
        top = module_name.split('.')[0]
        if top in sys.stdlib_module_names or top in sys.builtin_module_names:
            return True
        for candidate in _py_index(root).get(module_name.split('.')[-1], ()) + _py_index(root).get(top, ()):
            enqueue(candidate, via)
        return True

    pending_imports: list[tuple[str, Path, str]] = []
    run_files: set[Path] = {path}   # files run as programs (the entry, files named or loaded by path)
    live: set[Path] = set()

    def live_mains() -> set[Path]:
        """Files whose main() / __main__ block runs: programs, and modules whose main the closure uses."""
        used = {name.split('.')[-1] for facts in modules.values() for name in facts.main_refs}
        return {p for p, facts in modules.items()
                if p in run_files or facts.own_main_used or PurePosixPath(facts.me).stem in used}

    while True:
        while queue:
            current, via = queue.pop(0)
            name = rel(current, root)
            if via is not None:
                out.files.setdefault(name, f'imports {name}' + ('' if via == me else f' (via {via})'))
                if name in NOT_FOLLOWED:
                    continue
            facts = _module(current, root)
            modules[current] = facts
            sinks.append(facts.sink)
            for module_name, importer in facts.sink.imports:
                if not resolve_import(module_name, importer, name, False):
                    pending_imports.append((module_name, importer, name))
            for py in facts.sink.py_files:
                run_files.add(Path(os.path.normpath(root / py)))
                enqueue(root / py, name)
        live = live_mains()
        for current in modules:
            for py in modules[current].mutant_sink.py_files:
                run_files.add(Path(os.path.normpath(root / py)))
                enqueue(root / py, rel(current, root))
        for current in sorted(live):
            for py in modules[current].main_sink.py_files + modules[current].main_mutant_sink.py_files:
                run_files.add(Path(os.path.normpath(root / py)))
                enqueue(root / py, rel(current, root))
        # parameters: every use resolved with the values each call site in the closure passes
        _resolve_params(modules, root, resolved, live, resolved_mutant)
        for module_name, importer in resolved.imports + resolved_mutant.imports:
            if not resolve_import(module_name, importer, rel(importer, root), False):
                pending_imports.append((module_name, importer, rel(importer, root)))
        resolved.imports.clear()
        resolved_mutant.imports.clear()
        for py in resolved.py_files + resolved_mutant.py_files:
            run_files.add(Path(os.path.normpath(root / py)))
            enqueue(root / py, me)
        # sys.path entries found later can resolve earlier imports; then any repository module of that name
        retry, pending_imports = pending_imports, []
        for module_name, importer, via in retry:
            resolve_import(module_name, importer, via, True)
        if not queue:
            break
    make_uses, include_dirs, c_includes = set(), set(), set()
    for sink in sinks + [modules[p].main_sink for p in sorted(live)] + [resolved]:
        out.update(sink.deps)
        make_uses |= sink.make_uses
        include_dirs |= sink.include_dirs
    mutant_sinks = [m.mutant_sink for m in modules.values()] + \
        [modules[p].main_mutant_sink for p in sorted(live)] + [resolved_mutant]
    if any(m.deps.files or m.deps.dirs or m.deps.names or m.deps.globs or m.make_uses for m in mutant_sinks):
        mutant = Deps()
        for sink in mutant_sinks:
            mutant.update(sink.deps)
            for directory, target in sorted(sink.make_uses, key=lambda u: (u[0], u[1] or '')):
                mutant.update(target_deps(directory, target, root))
            for directory in sorted(sink.include_dirs):
                mutant.flat.setdefault(directory, f'mutant code compiles with -I {directory}')
        out.mutant = (out.mutant or Deps()).update(mutant)
    for facts in modules.values():
        c_includes |= facts.c_includes
    uses = sorted(make_uses, key=lambda u: (u[0], u[1] or ''))
    with concurrent.futures.ThreadPoolExecutor(4) as pool:   # the dry runs are independent subprocesses
        list(pool.map(lambda u: dry_run(u[0], u[1], root), uses))
    for directory, target in uses:
        out.update(target_deps(directory, target, root))
    # Sources the code compiles itself (cc ... -I D) and C text it writes ('#include "x.h"' in a string):
    # the headers they include through those directories.
    code = SOURCES | HEADERS
    sources = {p for p in out.files if _suffix(p) in code and (p not in out.targets or p in out.other)}
    search = tuple(root / d for d in sorted(include_dirs | set(out.dirs)))
    roots = [root / s for s in sorted(sources) if (root / s).is_file()]
    for name in sorted(c_includes):
        for directory in search:
            candidate = Path(os.path.normpath(directory / name))
            if candidate.is_file():
                roots.append(candidate)
                where = rel(candidate, root)
                if where:
                    out.add(where, f'generated C includes {where}')
                break
    for header in _includes(tuple(roots), search):
        where = rel(header, root)
        if where:
            out.add(where, f'compiled source includes {where}')
    if not roots:
        for directory in sorted(include_dirs):   # -I D with no source we can see: every header in D
            out.flat.setdefault(directory, f'{me} compiles with -I {directory}')
    return out


def _resolve_params(modules: dict[Path, _Module], root: Path, plain: _Sink, live: set = frozenset(),
                    mutant: _Sink | None = None) -> None:
    """Resolve every parameter use (A: values) with the arguments of the closure's call sites, through
    chains of parameters. An argument of a call no closure function receives (a library call) is a plain use.
    A function no call site reaches (a callback) keeps what its use names after the parameter, as a pattern."""
    by_file = {facts.me: facts for facts in modules.values()}
    by_name: dict[str, _Module] = {}
    for facts in modules.values():
        by_name.setdefault(PurePosixPath(facts.me).stem, facts)

    def target(facts, ref):
        owner = facts if ref[0] == '' else by_name.get(ref[0].split('.')[-1])
        return owner if owner is not None and ref[1] in owner.functions else None

    calls: dict[tuple[str, str], list] = {}
    referenced: set[tuple[str, str]] = set()
    for facts in modules.values():
        for ref, positional, keywords in facts.calls + (facts.main_calls if facts.path in live else []):
            owner = target(facts, ref)
            if owner is not None:
                calls.setdefault((owner.me, ref[1]), []).append((facts, positional, keywords))
        for name in facts.referenced:
            referenced.add((facts.me, name))
    mutant = mutant if mutant is not None else plain
    work = []
    for facts in modules.values():
        main = facts.path in live
        work += [(facts, value, context, line, 0, m)
                 for value, context, line, m in facts.param_uses + (facts.main_param_uses if main else [])]
        for value, ref, line, m in facts.deferred + (facts.main_deferred if main else []):
            if target(facts, ref) is None:   # not a closure function: the argument is used as it is
                if value.startswith('A:'):
                    work.append((facts, value, ('whole',), line, 0, m))
                else:
                    facts.apply(mutant if m else plain, value, ('whole',), line)
    applied = set()
    while work:
        facts, value, context, line, depth, m = work.pop()
        sink = mutant if m else plain
        if (value, context, line) in applied or depth > 6:
            continue
        applied.add((value, context, line))
        key, head, tail = _unsym(value)
        file, function, param = key.split('::')
        owner = by_file.get(file)
        if owner is None:
            continue
        sites = calls.get((file, function), [])
        if (not sites or (file, function) in referenced) and \
                any(part and '*' not in part for part in tail.split('/')[1:]):
            pattern = (_norm(head[2:]) or '') + '*' + tail if head[:2] == 'P:' else '*' + tail
            literal = owner._resolve('S:' + tail.lstrip('/')) if head == 'S:' else None
            if literal is not None and (root / literal).is_file():
                owner.apply(sink, 'P:' + literal, context if context[0] != 'bound' else ('whole',), line)
            elif pattern.endswith('.py'):
                sink.deps.fallback[line] = f'{line} builds a Python path from a parameter ({pattern})'
            else:
                for each in (pattern, pattern.rstrip('/') + '/*'):
                    sink.deps.globs.setdefault(each, f'{line} uses {pattern} (parameter, no call site)')
        for definition in owner.functions.get(function, []):
            names = [a.arg for a in definition.args.posonlyargs + definition.args.args]
            defaults = dict(zip(names[len(names) - len(definition.args.defaults):], definition.args.defaults))
            defaults.update({a.arg: d for a, d in zip(definition.args.kwonlyargs, definition.args.kw_defaults)
                             if d is not None})
            if isinstance(owner.parents.get(definition), ast.ClassDef) and names and names[0] == param:
                continue   # self
            for caller, positional, keywords in sites:
                if positional is None:
                    continue
                if param in names and names.index(param) < len(positional):
                    arguments = positional[names.index(param)]
                elif param in keywords:
                    arguments = keywords[param]
                elif param in defaults:
                    arguments, caller = owner.fold(defaults[param]), owner
                else:
                    continue
                for argument in arguments or ():
                    result = _instantiate(value, argument)
                    if result is None:
                        continue
                    if result.startswith('A:'):
                        work.append((caller, result, context, line, depth + 1, m))
                    elif context[0] != 'bound':
                        owner.apply(sink, result, context, line)


def python_deps(path: Path, root: Path = ROOT, tooling: bool | str = True) -> Deps:
    """A Python file's inputs: itself, the repository modules it imports or loads, the repository paths its
    code builds (classified by use) and what those reach. TOOLING=False leaves the selection tooling out
    (validator rows); 'direct' keeps it only where PATH itself imports or names it (test modules: the tests of
    a tool, not every test that reaches it through a validator); True keeps it all (cache keys). A fresh copy:
    callers may add to it."""
    return _closure(Path(os.path.normpath(path)), root, tooling).copy()


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


@_memo
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


@_memo
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


@_memo
def dry_run(directory: str, target: str | None, root: Path = ROOT, makefile_text: str | None = None) -> str | None:
    """`make -nB [target]` in DIRECTORY (with MAKEFILE_TEXT in place of its Makefile), or None if it fails."""
    command = ['make', '-C', str(root / directory), '-nB'] + ([target] if target else [])
    if makefile_text is None:
        done = subprocess.run(command, capture_output=True, text=True)
        return done.stdout if not done.returncode else None
    with tempfile.TemporaryDirectory() as folder:
        alternate = Path(folder) / 'Makefile'
        alternate.write_text(makefile_text)
        done = subprocess.run(command[:3] + ['-f', str(alternate)] + command[3:], capture_output=True, text=True)
        return done.stdout.replace(str(alternate), 'Makefile') if not done.returncode else None


def _commands(text: str) -> list[list[str]]:
    """The simple commands of dry-run output (lines split at ;, &&, ||, |)."""
    out = []
    for line in text.splitlines():
        try:
            words = shlex.split(line, comments=False)
        except ValueError:
            words = line.split()
        current: list[str] = []
        for word in words:
            if word in (';', '&&', '||', '|'):
                if current:
                    out.append(current)
                current = []
            else:
                current.append(word)
        if current:
            out.append(current)
    return out


def _mm_command(words: list[str]) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """(compiler flags, sources) of a compile command, without outputs, link inputs and dependency flags."""
    if not words or os.path.basename(words[0]) not in COMPILERS:
        return None
    flags, sources, skip = [words[0]], [], False
    for i, word in enumerate(words[1:], 1):
        if skip:
            skip = False
            continue
        if word in ('-o', '-MF', '-MT', '-MQ', '-framework', '-install_name', '-arch', '>', '2>'):
            skip = True
            if word == '-arch':
                flags += [word, words[i + 1]] if i + 1 < len(words) else []
            continue
        if word in ('-c', '-MD', '-MMD', '-MP', '-M', '-MM', '-shared', '-dynamiclib', '-S', '-E', '-MG'):
            continue
        if word.startswith(('-l', '-L', '-Wl,', '-flto')) or word.endswith(('.o', '.a', '.dylib', '.so', '.tbd')):
            continue
        if not word.startswith('-') and _suffix(word) in SOURCES:
            sources.append(word)
        else:
            flags.append(word)
    return (tuple(flags), tuple(sources)) if sources else None


_MM: dict[tuple[str, tuple[str, ...], str], tuple[str, ...] | None] = {}


def _mm_batch(base: str, flags: tuple[str, ...], sources: tuple[str, ...]) -> None:
    """Headers the compiler reads for each of SOURCES with FLAGS (relative to BASE), from one -MM -MG call per
    flag set; a failing batch is retried per source, and a failing source records None."""
    todo = tuple(s for s in dict.fromkeys(sources) if (base, flags, s) not in _MM)
    if not todo:
        return
    done = subprocess.run([*flags, '-MM', '-MG', *todo], cwd=base, capture_output=True, text=True, timeout=600)
    if done.returncode:
        if len(todo) == 1:
            _MM[(base, flags, todo[0])] = None
            return
        for source in todo:
            _mm_batch(base, flags, (source,))
        return
    rules = re.split(r'(?m)^(?=\S[^:\n]*:)', done.stdout.replace('\\\n', ' '))
    found: dict[str, tuple[str, ...]] = {}
    wanted = set(todo)
    for rule in rules:   # "x.o: [SDKSettings.json] x.c headers...": the rule of the source it lists
        words = [w for w in rule.split() if not w.endswith(':')]
        source = next((w for w in words if w in wanted), None)
        if source is not None:
            found.setdefault(source, tuple(words))
    for source in todo:
        _MM[(base, flags, source)] = found.get(source)


def _mm(base: str, flags: tuple[str, ...], source: str) -> tuple[str, ...] | None:
    _mm_batch(base, flags, (source,))
    return _MM[(base, flags, source)]


def _fresh_d(dfile: Path, base: Path) -> tuple[str, ...] | None:
    """The paths a .d file lists, if it is newer than all of them (so it describes the current sources)."""
    try:
        stamp = dfile.stat().st_mtime
        words = dfile.read_text(errors='replace').replace('\\\n', ' ').split()
    except OSError:
        return None
    paths = tuple(w for w in words if not w.endswith(':'))
    for word in paths:
        try:
            if (base / word).stat().st_mtime > stamp:
                return None
        except OSError:
            return None   # a listed file was deleted or renamed: stale
    return paths


@_memo
def target_deps(directory: str, target: str | None, root: Path = ROOT) -> Deps:
    """Every repository file a full rebuild of TARGET in DIRECTORY reads (make -nB dry run; headers from fresh
    .d files or the compiler's -MM)."""
    base = root / directory
    label = f'make -C {directory} {target or "(default goal)"}'
    text = dry_run(directory, target, root)
    if text is None:
        deps = makefile_deps(directory, root)  # an incomplete dry run cannot prove independence
        deps.files.setdefault(f'{directory}/Makefile', f'{label} fails; uses {directory}/Makefile')
        return deps
    deps = Deps()
    deps.makefiles.setdefault(f'{directory}/Makefile', set()).add((directory, target))
    # Included make fragments can change flags/rules without appearing in recipe output.
    for name, why in makefile_deps(directory, root).files.items():
        deps.files.setdefault(name, why)
    outputs, include_dirs, compiles = [], [], []
    for words in _commands(text):
        parsed = _mm_command(words)
        if parsed is not None:
            compiles.append((words, parsed))
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
                    pass  # search path; the compiler's headers below identify actual headers
                else:
                    deps.dirs.setdefault(where, f'{label} reads {where}/')
            else:
                deps.files.setdefault(where, f'{label} compiles {where}')
                if path.suffix in SOURCES:
                    parent = rel(path.parent, root)
                    if parent:
                        deps.src_dirs.setdefault(parent, f'{label} compiles from')
                elif path.suffix == '.py':
                    deps.update(python_deps(path, root))
            if flag == '-I' and path.is_dir():
                include_dirs.append(path)
    # Headers: a fresh .d file per output, else -MM -MG per compiled source, else the textual closure.
    fresh: dict[str, tuple[str, ...]] = {}
    for output in outputs:
        out = base / output
        for dfile in (out.with_suffix('.d'), Path(str(out) + '.d')):
            listed = _fresh_d(dfile, base) if dfile.is_file() else None
            if listed:
                fresh[output] = listed
    jobs = []
    for words, (flags, sources) in compiles:
        output = words[words.index('-o') + 1] if '-o' in words[:-1] else None
        if output in fresh:
            for word in fresh[output]:
                _header(deps, base, word, root, label)
            continue
        jobs += [(flags, source) for source in sources if (base / source).is_file()]
    textual: list[Path] = []
    groups: dict[tuple[str, ...], list[str]] = {}
    for flags, source in dict.fromkeys(jobs):
        groups.setdefault(flags, []).append(source)
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        list(pool.map(lambda item: _mm_batch(str(base), item[0], tuple(item[1])), groups.items()))
    results = [((flags, source), _MM.get((str(base), flags, source))) for flags, source in dict.fromkeys(jobs)]
    for (flags, source), listed in results:
        if listed is None:
            textual.append(base / source)
            continue
        for word in listed:
            _header(deps, base, word, root, label)
    if textual:
        headers = _includes(tuple(textual), tuple(dict.fromkeys(include_dirs)))
        if any(re.search(r'^\s*#\s*(?:include|import)\s+[^<\"\s]', p.read_text(errors='replace'), re.M)
               for p in [*textual, *headers]):
            for directory_path in include_dirs:
                where = rel(directory_path, root)
                if where:
                    deps.flat[where] = f'{label} has computed includes in {where}/'
        for header in headers:   # #include "..." (closure)
            where = rel(header, root)
            if where:
                deps.files.setdefault(where, f'{label} includes {where}')
    for where in deps.files:   # every file above is an input only through this target's build
        deps.targets.setdefault(where, set()).add((directory, target))
    return deps


def _header(deps: Deps, base: Path, word: str, root: Path, label: str) -> None:
    path = Path(os.path.normpath(base / word))
    where = rel(path, root)
    if where and path.is_file():
        deps.files.setdefault(where, f'{label} includes {where}')


@_memo
def makefile_unchanged(directory: str, target: str | None, base_text: str | None, root: Path = ROOT) -> bool:
    """True when TARGET's dry run with the base Makefile text equals the current one (a Makefile change that
    cannot alter how TARGET is built). Unknown base text or a failing dry run: False."""
    if base_text is None:
        return False
    current = dry_run(directory, target, root)
    return current is not None and current == dry_run(directory, target, root, base_text)


def same_make(units: dict[str, Deps], changed: list[str], base: str | None, root: Path = ROOT) -> frozenset:
    """(dir, target) pairs whose dry run every changed Makefile leaves identical."""
    if base is None:
        return frozenset()
    out = set()
    for path in changed:
        if not path.endswith('/Makefile'):
            continue
        uses = {u for deps in units.values() for u in deps.makefiles.get(path, ())}
        if not uses:
            continue
        try:
            text = git('show', f'{base}:{path}', root=root)
        except SystemExit:
            continue
        for directory, target in uses:
            if makefile_unchanged(directory, target, text, root):
                out.add((directory, target))
    return frozenset(out)


# ---------------------------------------------------------------------------------------------
# selection

def clear_caches(root: Path | None = None) -> None:
    """Forget every parsed file, dry run and compiler answer about ROOT (default: all), for a caller that edits
    that tree in-process."""
    for function in (_py_index, _module, _closure, make_targets, _quoted_includes, dry_run, target_deps,
                     makefile_unchanged, target_change):
        function.cache_clear(root)
    for key in [k for k in _MM if root is None or k[0].startswith(str(root))]:
        del _MM[key]
    affected_symbols.clear_cache(root)
    suites = sys.modules.get('run_test_suites')
    if root is None and suites is not None and hasattr(suites, '_unit_deps'):
        suites._unit_deps.cache_clear()


def _base_bytes(base: str, path: str, root: Path) -> bytes | None:
    done = subprocess.run(['git', '-C', str(root), 'show', f'{base}:{path}'], capture_output=True)
    return done.stdout if not done.returncode else None


@_memo
def target_change(directory: str, target: str | None, base: str, changed: tuple[str, ...],
                  root: Path = ROOT) -> affected_symbols.Change:
    """Which exported symbols of make TARGET in DIRECTORY the diff from BASE (CHANGED) changes."""
    label = f'make -C {directory} {target or "(default goal)"}'
    text = dry_run(directory, target, root)
    if text is None:
        return affected_symbols.Change(label, fallback=f'{label} has no dry run')
    cwd = root / directory
    real = os.path.realpath   # clang sees resolved paths (/private/var for /var on macOS)
    base_files = {real(root / p): _base_bytes(base, p, root) for p in changed if _suffix(p) in SOURCES | HEADERS}

    def unit_inputs(flags, source):
        listed = _mm(str(cwd), tuple(flags), source)
        if listed is None:
            return None
        return {real(os.path.join(str(cwd), w)) for w in listed}
    return affected_symbols.analyze(label, cwd, root, _commands(text), _mm_command, base_files, unit_inputs)


def used_symbols(deps: Deps, exports: set[str]) -> tuple[set[str], str | None]:
    """The exports a unit's Python code can name, or all of them with the reason when a lookup is unbounded."""
    if deps.sym_dynamic:
        return set(exports), next(iter(deps.sym_dynamic.values()))
    used = exports & deps.symbols
    if deps.sym_patterns:
        pieces = fragments(deps.symbols)
        for template in deps.sym_patterns:
            used |= {e for e in exports - used if template_matches(template, e, pieces)}
    return used, None


def symbol_verdict(deps: Deps, path: str, targets: set, base: str, changed: list[str], root: Path,
                   same_make: frozenset = frozenset()) -> str | None:
    """Why PATH, compiled only into TARGETS (and mutant copies of them), still affects the unit (a changed
    symbol it uses, or a conservative fallback), or None when no symbol it uses changed."""
    copies = deps.mutant_route(path, same_make, root)
    for directory, target in sorted(targets, key=lambda u: (u[0], u[1] or '')):
        change = target_change(directory, target, base, tuple(sorted(changed)), root)
        if change.fallback:
            return f'{SYMBOL_FALLBACK}: {change.fallback}'
        if copies and change.link_changed:   # mutant builds list their units by hand
            return f'{SYMBOL_FALLBACK}: mutant builds copy these sources and {change.link_changed}'
        if change.roots_always:
            return f'{change.label}: {sorted(change.roots_always)[0]} reaches a change'
        used, dynamic = used_symbols(deps, change.exports)
        hit = sorted(used & set(change.changed))
        if hit:
            if dynamic:
                return f'{SYMBOL_FALLBACK}: {dynamic}'
            node = change.changed[hit[0]]
            return f'uses {hit[0]}' + (f' (reaches {node})' if node != hit[0] else '') + ' changed' + (
                f' (+{len(hit) - 1} symbols)' if len(hit) > 1 else '')
    return None


def select(units: dict[str, Deps], changed: list[str], infra: dict[str, str] | None = None,
           mapped: tuple[str, ...] = (), base: str | None = None, root: Path = ROOT,
           unmapped_selects_all: bool = True, symbols: bool = False,
           pruned: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    """{unit: [reasons]} for every unit some changed path can affect.

    INFRA paths (the caller's, path -> description) select every unit. A unit with fallback reasons is
    selected by every changed path that is not documentation or TOOLING. UNMAPPED_SELECTS_ALL (test suites):
    a non-doc path no unit depends on selects everything; validator rows pass False, because their inputs
    are derived per row (a row whose inputs cannot be derived carries its own fallback).

    SYMBOLS (validator rows, TEST-SPEED-005): a C source or header that is an input only because a make target
    the unit builds compiles it selects the unit only if an exported symbol the unit's code names changed
    (affected_symbols); PRUNED collects {unit: [paths dropped that way]}."""
    shared = {path: 'shared infrastructure' for path in INFRA}
    shared.update(infra or {})
    keep = same_make(units, changed, base, root)
    hit_all = [f'{path}: {shared[path]} (selects everything)' for path in changed if path in shared]
    if unmapped_selects_all:
        for path in changed:
            if path not in mapped and path not in shared and not is_doc(path) and \
                    not any(deps.why(path, keep, root) for deps in units.values()):
                hit_all.append(f'{path}: unmapped input (selects everything)')
    out: dict[str, list[str]] = {}
    for name, deps in units.items():
        reasons = list(hit_all)
        fallback = next(iter(deps.fallback.values()), None)
        dropped, candidates = [], []
        for path in changed:
            if path in shared:
                continue
            reason = deps.why(path, keep, root)
            if reason and symbols and base is not None and _suffix(path) in SOURCES | HEADERS:
                targets = deps.make_only(path, keep, root)
                if targets:
                    candidates.append((path, reason, targets))
                    continue
                if path in deps.targets:   # name the route that keeps the make target from being pruned
                    reason = deps._why(path, keep, root, compiled=False) or reason
            if reason:
                reasons.append(f'{path}: {reason}')
            elif fallback and not is_doc(path) and path not in TOOLING:
                reasons.append(f'{path}: inputs not derivable ({fallback})')
        # Paths compiled only into libraries the unit builds: ask the symbol analysis only when nothing else
        # selects the unit (the answer cannot change the selection otherwise).
        for path, reason, targets in candidates:
            if reasons:
                reasons.append(f'{path}: {reason}')
                continue
            verdict = symbol_verdict(deps, path, targets, base, changed, root, keep)
            if verdict is None:
                dropped.append(path)
            else:
                reasons.append(f'{path}: {reason}; {verdict}')
        if reasons:
            dropped = []
        if reasons:
            out[name] = reasons
        if dropped and pruned is not None:
            pruned[name] = dropped
    return out


def fallback_units(units: dict[str, Deps]) -> dict[str, list[str]]:
    """{unit: [why its inputs are not fully derivable]}."""
    return {name: list(deps.fallback.values()) for name, deps in units.items() if deps.fallback}


def show(selected: dict[str, list[str]], total: int, noun: str, fallback: dict[str, list[str]] | None = None,
         pruned: dict[str, list[str]] | None = None) -> str:
    lines = [f'affected: {len(selected)} of {total} {noun} selected']
    for name, reasons in selected.items():
        more = f' (+{len(reasons) - MAX_REASONS} more)' if len(reasons) > MAX_REASONS else ''
        lines.append(f'  {name}: ' + '; '.join(reasons[:MAX_REASONS]) + more)
    symbol = {n: [r for r in rs if SYMBOL_FALLBACK in r] for n, rs in selected.items()}
    symbol = {n: rs for n, rs in symbol.items() if rs}
    if symbol:
        lines.append(f'affected: {len(symbol)} {noun} kept by the symbol-level fallback (change not attributable):')
        for name, reasons in symbol.items():
            lines.append(f'  {name}: ' + reasons[0])
    if pruned:
        dropped = {n: p for n, p in pruned.items() if n not in selected}
        if dropped:
            lines.append(f'affected: {len(dropped)} {noun} not selected: they build a changed library but use no '
                         f'changed symbol ({", ".join(sorted(dropped))})')
    if fallback:
        lines.append(f'affected: {len(fallback)} {noun} use the conservative fallback (inputs not derivable):')
        for name, reasons in fallback.items():
            lines.append(f'  {name}: ' + '; '.join(reasons[:MAX_REASONS]))
    return '\n'.join(lines)
