"""Parse CMake configuration diagnostics from CI logs (stdlib, Python 3.10+).

Produces gcc_clang.Diagnostic objects. Only parses messages; no probabilities.
"""
from __future__ import annotations

import re
from typing import Iterable
from gcc_clang import Diagnostic

ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
HEADER = re.compile(
    r'^CMake (?P<severity>Error|Warning(?: \(dev\))?|Deprecation Warning) '
    r'at (?P<file>.+?):(?P<line>\d+) \((?P<command>[^)]*)\):\s*$'
)
MESSAGE_TARGET = re.compile(r'\btarget\s+["\']([^"\']+)["\']', re.I)


def _make_diagnostic(header: re.Match[str], body: list[str]) -> Diagnostic:
    message = ' '.join(line.strip() for line in body if line.strip())
    # Extract a useful target name when CMake explicitly names it.
    target = MESSAGE_TARGET.search(message)
    symbol = target.group(1) if target else None
    # Missing source paths are retained in the message; they are not C identifiers.
    severity = 'error' if header['severity'] == 'Error' else 'warning'
    return Diagnostic(category='build', severity=severity, message=message,
                      file=header['file'], line=int(header['line']),
                      column=None, symbol=symbol)


def parse_log(lines: Iterable[str], *, include_warnings: bool = False) -> list[Diagnostic]:
    """Recognize `CMake Error at CMakeLists.txt:5 (command):` blocks.

    Stop at the next unindented log line; allow blank lines inside messages.
    """
    result: list[Diagnostic] = []
    header = None
    body: list[str] = []

    def flush() -> None:
        if header is not None:
            d = _make_diagnostic(header, body)
            if include_warnings or d.severity == 'error':
                result.append(d)

    for raw in lines:
        line = ANSI.sub('', raw).rstrip('\r\n')
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
