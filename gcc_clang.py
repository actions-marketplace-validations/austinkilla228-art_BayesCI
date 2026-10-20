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
COMPILER = re.compile(r'^(?P<location>.+):\s*(?P<severity>fatal error|error|warning|note):\s*(?P<message>.*)$')
LOCATION = re.compile(r'^(?P<file>.+?):(?P<line>\d+)(?::(?P<column>\d+))?$')
LINKER = re.compile(r'\b(?:undefined reference to|undefined symbol:|multiple definition of|duplicate symbol:)\s*(?P<symbol>.+)', re.I)
LINKER_SOURCE = re.compile(r'(?:\b(?:ld|ld\.lld|lld|collect2)(?:\.exe)?\b|\.(?:o|obj|a|so)(?::|\b)|\bld:)', re.I)
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


def parse_line(raw: str) -> Diagnostic | None:
    line = ANSI.sub('', raw).strip()
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
    link = LINKER.search(line)
    if link and LINKER_SOURCE.search(line):
        symbol = link['symbol'].strip().strip("`'‘’\" ")
        # Some ld messages include trailing annotation; preserve full original message.
        return Diagnostic(category='linker', severity='error', message=line, symbol=symbol)
    # lld frequently prints "ld.lld: error: undefined symbol: foo" (handled above).
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
