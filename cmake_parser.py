"""Parse CMake configuration diagnostics from CI logs (stdlib, Python 3.10+).

Produces gcc_clang.Diagnostic objects. Only parses messages; no probabilities.
"""
from __future__ import annotations

import re
from typing import Iterable
from gcc_clang import Diagnostic

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
LOG_TIMESTAMP = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)\s+')
# Formats seen in different CMake versions:
#   CMake Error at CMakeLists.txt:5 (target_sources):
#   CMake Error at CMakeLists.txt:5:
#   CMake Error in CMakeLists.txt:
#   CMake Error: Could not create named generator ...
HEADER = re.compile(
    r'^CMake (?P<severity>Error|Warning(?: \(dev\))?|Deprecation Warning)'
    r'(?: at (?P<file>.+?):(?P<line>\d+)(?: \((?P<command>[^)]*)\))?'
    r'| in (?P<in_file>.+?)|):\s*(?P<initial>.*)$'
)
MESSAGE_TARGET = re.compile(r'\btarget\s+["\']([^"\']+)["\']', re.I)


def _make_diagnostic(header: re.Match[str], body: list[str]) -> Diagnostic:
    message = ' '.join(part for part in [header['initial'].strip(),
                       *(line.strip() for line in body if line.strip())] if part)
    target = MESSAGE_TARGET.search(message)
    symbol = target.group(1) if target else None
    severity = 'error' if header['severity'] == 'Error' else 'warning'
    file = header['file'] or header['in_file']
    line = int(header['line']) if header['line'] else None
    return Diagnostic(category='build', severity=severity, message=message,
                      file=file, line=line, column=None, symbol=symbol)


def parse_log(lines: Iterable[str], *, include_warnings: bool = False) -> list[Diagnostic]:
    """Read location-based and generic CMake Error/Warning messages.

    Stop at the next unindented log line; allow blank lines inside messages.
    """
    result: list[Diagnostic] = []
    header: re.Match[str] | None = None
    body: list[str] = []

    def flush() -> None:
        if header is not None:
            d = _make_diagnostic(header, body)
            if include_warnings or d.severity == 'error':
                result.append(d)

    for raw in lines:
        line = LOG_TIMESTAMP.sub('', ANSI.sub('', raw).rstrip('\r\n'))
        match = HEADER.match(line)
        if match:
            flush()
            header = match
            body = []
            continue
        if header is not None:
            if not line.strip() or line[:1].isspace():
                body.append(line)
            else:
                flush()
                header = None
                body = []
    flush()
    return result
