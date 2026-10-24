"""Streaming GCC/Clang/GNU ld/lld diagnostic parser; Python 3.10+, stdlib only.

Extracts evidence, not Bayesian likelihoods. Unrecognized lines are ignored.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import re
import sys
from typing import Iterable, Iterator

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
# GitHub Actions downloaded job logs may have an ISO timestamp before each line.
LOG_TIMESTAMP = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)\s+')
COMPILER = re.compile(r'^(?P<location>.+):\s*(?P<severity>fatal error|error|warning|note):\s*(?P<message>.*)$')
LOCATION = re.compile(r'^(?P<file>.+?):(?P<line>\d+)(?::(?P<column>\d+))?$')
# GCC/Clang driver errors can have no source-file location, e.g.
#   cc: error: unrecognized command-line option '-fno-such-option'
#   /usr/bin/clang++: error: unknown argument: '-fno-such-option'
# Treat these as build diagnostics so CMake/Make changes can be matched.
DRIVER_ERROR = re.compile(
    r'^(?:.*[\\/])?(?:[A-Za-z0-9_+.]+-)*'
    r'(?:gcc|g\+\+|clang\+\+|clang-cl|clang|cc|c\+\+)'
    r'(?:-[0-9.]+)?(?:\.exe)?:\s*'
    r'(?P<severity>fatal error|error|warning):\s*(?P<message>.+)$',
    re.I,
)
LINKER = re.compile(r'\b(?:undefined reference to|undefined symbol:|multiple definition of|duplicate symbol:)\s*(?P<symbol>.+)', re.I)
LINKER_SOURCE = re.compile(
    r'(?:\b(?:ld|ld\.lld|lld|lld-link|collect2|link)(?:\.exe)?\b|\.(?:o|obj|a|so)(?::|\b)|\bld:)',
    re.I,
)
# Missing libraries reported by GNU ld, Clang lld, Apple ld and MSVC LINK.
LIBRARY_PATTERNS = (
    re.compile(r'\bcannot find\s+(?P<library>-l[^\s:;,]+)', re.I),
    re.compile(r'\b(?:library not found for|unable to find library)\s+(?P<library>-l[^\s:;,]+)', re.I),
    re.compile(r'\bcannot find\s+(?P<library>[^\s:;,]+\.(?:a|so(?:\.\d+)*|dylib|lib))', re.I),
    re.compile(r'\b(?:cannot open (?:input )?file|could not open)\s+[\'\"]?(?P<library>[^\'\"\s:;,]+\.(?:a|so(?:\.\d+)*|dylib|lib))', re.I),
    re.compile(r'\b(?:cannot open|unable to open)\s+(?P<library>[^\s:;,]+\.(?:a|so(?:\.\d+)*|dylib|lib))', re.I),
)
SYMBOL_PATTERNS = [
    re.compile(r"(?:use of undeclared identifier|implicit declaration of function|unknown type name|no member named|undeclared identifier)\s+['‘`]([^'’`]+)['’`]", re.I),
    re.compile(r"['‘`]([^'’`]+)['’`]\s+(?:undeclared|was not declared)", re.I),
    re.compile(r"(?:call to undeclared function|no matching function for call to)\s+['‘`]([^'’`]+)['’`]", re.I),
]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    category: str
    severity: str
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    symbol: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def classify(message: str, *, linker: bool = False) -> str:
    """Coarse labels for feature extraction, NOT probability weights."""
    if linker:
        return 'linker'
    s = message.lower()
    if any(x in s for x in ('file not found', 'no such file or directory', 'cannot find', 'header file')):
        return 'header'
    if any(x in s for x in ('undeclared', 'not declared', 'undefined identifier', 'no member named')):
        return 'symbol'
    if any(x in s for x in ('unknown type name', 'incompatible type', 'invalid conversion', 'cannot convert', 'type mismatch')):
        return 'type'
    if any(x in s for x in ('expected ', 'extraneous ', 'before token', 'stray ', 'missing terminating')):
        return 'syntax'
    return 'other'


def extract_symbol(message: str) -> str | None:
    for pattern in SYMBOL_PATTERNS:
        match = pattern.search(message)
        if match:
            return match.group(1).strip()
    return None


def _clean_log_line(raw: str) -> str:
    return LOG_TIMESTAMP.sub('', ANSI.sub('', raw).strip())


def _linker_symbol(text: str) -> str:
    """Extract just the symbol; do not swallow the `first defined here` suffix."""
    text = text.strip()
    closing = {'`': "'", "'": "'", '"': '"', '‘': '’'}
    if text and text[0] in closing:
        end = text.find(closing[text[0]], 1)
        if end != -1:
            return text[1:end]
    return text.split(';', 1)[0].strip("`'‘’\" ")


def _library_symbol(library: str) -> str | None:
    """Use the -lNAME name when possible; paths are not C identifiers."""
    if library.startswith('-l'):
        name = library[2:]
        return name if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name) else None
    return None


def parse_line(raw: str) -> Diagnostic | None:
    line = _clean_log_line(raw)
    match = COMPILER.match(line)
    if match:
        location = LOCATION.match(match['location'])
        if location:
            msg = match['message']
            sev = match['severity']
            return Diagnostic(
                category=classify(msg), severity=sev, message=msg,
                file=location['file'], line=int(location['line']),
                column=int(location['column']) if location['column'] else None,
                symbol=extract_symbol(msg),
            )

    driver = DRIVER_ERROR.match(line)
    if driver:
        return Diagnostic(
            category='build', severity=driver['severity'],
            message=driver['message'],
        )

    link = LINKER.search(line)
    if link and LINKER_SOURCE.search(line):
        return Diagnostic(category='linker', severity='error', message=line,
                          symbol=_linker_symbol(link['symbol']))

    if LINKER_SOURCE.search(line):
        for pattern in LIBRARY_PATTERNS:
            missing = pattern.search(line)
            if missing:
                library = missing['library']
                return Diagnostic(category='linker', severity='error', message=line,
                                  symbol=_library_symbol(library))
    return None


def iter_diagnostics(lines: Iterable[str], *, include_warnings: bool = False) -> Iterator[Diagnostic]:
    """Stream diagnostics. Default emits only errors, including fatal errors."""
    for line in lines:
        d = parse_line(line)
        if d is not None and (include_warnings or 'error' in d.severity):
            yield d


def parse_log(lines: Iterable[str], *, include_warnings: bool = False) -> list[Diagnostic]:
    return list(iter_diagnostics(lines, include_warnings=include_warnings))


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract GCC/Clang/ld diagnostics from a CI log')
    parser.add_argument('log', nargs='?', help='Path to log; otherwise read stdin')
    parser.add_argument('--warnings', action='store_true', help='Include warnings and notes')
    args = parser.parse_args()
    if args.log:
        with open(args.log, encoding='utf-8', errors='replace') as stream:
            diagnostics = parse_log(stream, include_warnings=args.warnings)
    else:
        diagnostics = parse_log(sys.stdin, include_warnings=args.warnings)
    print(json.dumps([d.to_dict() for d in diagnostics], indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
