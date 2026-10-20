"""Minimal Git-diff evidence extraction for BayesCI (Python 3.10+, stdlib).

Inputs: gcc_clang.Diagnostic objects (or equivalent dicts) and per-commit
unified diff strings. Outputs: F/S/B observations (1, 0, or None).

This module does not estimate likelihoods or probabilities.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
import argparse
import json
import re
from typing import Iterable, Mapping, Any

DIFF_HEADER = re.compile(r'^diff --git a/(.*?) b/(.*)$')
HUNK_HEADER = re.compile(r'^@@ .*? @@')
BUILD_FILES = {'cmakelists.txt', 'makefile', 'gnumakefile', 'meson.build',
               'build.gradle', 'build.gradle.kts', 'pom.xml', 'cargo.toml',
               'configure.ac', 'configure.in', 'setup.py', 'pyproject.toml'}
BUILD_SUFFIXES = ('.cmake', '.mk', '.gradle', '.gradle.kts')
SYMBOL_WORD = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')


@dataclass(frozen=True, slots=True)
class Features:
    file: int | None
    symbol: int | None
    build: int | None

    def to_dict(self) -> dict[str, int | None]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ChangedFile:
    old_path: str
    new_path: str
    changed_lines: tuple[str, ...]


def _norm(path: str) -> str:
    path = path.replace('\\', '/').strip()
    if path.startswith(('a/', 'b/')):
        path = path[2:]
    # Normalize harmless ./ and repeated separators, but not arbitrary suffix matches.
    parts = []
    for part in path.split('/'):
        if part in ('', '.'):
            continue
        if part == '..' and parts and parts[-1] != '..':
            parts.pop()
        else:
            parts.append(part)
    return '/'.join(parts)


def _same_file(diagnostic_path: str, changed_path: str) -> bool:
    a, b = _norm(diagnostic_path), _norm(changed_path)
    if not a or not b or b == 'dev/null':
        return False
    return a == b or a.endswith('/' + b) or b.endswith('/' + a)


def parse_unified_diff(diff: str) -> list[ChangedFile]:
    """Extract changed paths and +/- content; ignore diff metadata/context.

    Expects `git diff`/`git show` with `diff --git` headers. Handles renames
    with ordinary Git headers; does not interpret binary patches.
    """
    files: list[ChangedFile] = []
    old = new = None
    changes: list[str] = []
    in_hunk = False

    def flush() -> None:
        if old is not None and new is not None:
            files.append(ChangedFile(old, new, tuple(changes)))

    for line in diff.splitlines():
        m = DIFF_HEADER.match(line)
        if m:
            flush()
            old, new = _norm(m.group(1)), _norm(m.group(2))
            changes = []
            in_hunk = False
            continue
        if old is None:
            continue
        if line.startswith('rename from '):
            old = _norm(line[len('rename from '):])
        elif line.startswith('rename to '):
            new = _norm(line[len('rename to '):])
        elif line.startswith('--- '):
            value = line[4:]
            if value != '/dev/null':
                old = _norm(value)
        elif line.startswith('+++ '):
            value = line[4:]
            if value != '/dev/null':
                new = _norm(value)
        elif HUNK_HEADER.match(line):
            in_hunk = True
        elif line.startswith(('GIT binary patch', 'Binary files ')):
            in_hunk = False
        elif in_hunk and line[:1] in ('+', '-'):
            changes.append(line[1:])
    flush()
    return files


def _get(diagnostic: Any, field: str) -> Any:
    return diagnostic.get(field) if isinstance(diagnostic, Mapping) else getattr(diagnostic, field, None)


def _is_build_file(path: str) -> bool:
    p = _norm(path).lower()
    name = PurePosixPath(p).name
    return name in BUILD_FILES or name.endswith(BUILD_SUFFIXES) or p.startswith('.github/workflows/') or p == '.gitlab-ci.yml'


def _symbol_on_changed_line(symbol: str, changed_line: str) -> bool:
    # Avoid substring false positives: `parse` must not match `parse_config`.
    if not symbol or not SYMBOL_WORD.fullmatch(symbol):
        return False
    return symbol in SYMBOL_WORD.findall(changed_line)


def extract_for_commit(diagnostics: Iterable[Any], diff: str) -> Features:
    """Aggregate evidence over diagnostics for a single commit.

    1 = any supported diagnostic matches; 0 = evaluated, no match;
    None = unavailable/not applicable. `build` is a weak, coarse indicator,
    only evaluated for linker/header/build diagnostics.
    """
    diagnostics = list(diagnostics)
    changed = parse_unified_diff(diff)
    if not diagnostics:
        return Features(None, None, None)

    files = [_get(d, 'file') for d in diagnostics]
    symbols = [_get(d, 'symbol') for d in diagnostics]
    categories = [(_get(d, 'category') or '').lower() for d in diagnostics]

    known_files = [p for p in files if isinstance(p, str) and p.strip()]
    known_symbols = [s for s in symbols if isinstance(s, str) and SYMBOL_WORD.fullmatch(s)]

    file_match = (int(any(_same_file(p, path)
                          for p in known_files for f in changed
                          for path in (f.old_path, f.new_path)))
                  if known_files else None)
    symbol_match = (int(any(_symbol_on_changed_line(s, line)
                            for s in known_symbols for f in changed
                            for line in f.changed_lines))
                    if known_symbols else None)
    relevant_build_error = any(cat in {'linker', 'header', 'build'} for cat in categories)
    build_match = (int(any(_is_build_file(f.old_path) or _is_build_file(f.new_path)
                           for f in changed)) if relevant_build_error else None)
    return Features(file_match, symbol_match, build_match)


def extract_features(diagnostics: Iterable[Any], diffs: Mapping[str, str]) -> dict[str, dict[str, int | None]]:
    """Return {commit_sha: {'file': ..., 'symbol': ..., 'build': ...}}.

    `diffs` maps each commit SHA to a unified diff (`git show --format= --find-renames SHA`).
    """
    diagnostics = list(diagnostics)
    return {sha: extract_for_commit(diagnostics, diff).to_dict()
            for sha, diff in diffs.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description='Extract F/S/B evidence from diagnostics and Git diffs')
    ap.add_argument('--diagnostics', required=True, help='JSON array emitted by gcc_clang.py')
    ap.add_argument('--diffs', required=True, help='JSON object {SHA: unified_diff_text}')
    args = ap.parse_args()
    with open(args.diagnostics, encoding='utf-8') as f:
        diagnostics = json.load(f)
    with open(args.diffs, encoding='utf-8') as f:
        diffs = json.load(f)
    print(json.dumps(extract_features(diagnostics, diffs), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
