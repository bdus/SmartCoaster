"""Minimal S-expression reader/writer for KiCad 9 files.

Strings are double quoted with backslash escapes; everything else is an atom.
`parse()` returns nested lists whose scalars are `Atom` (bare token) or `QStr`
(quoted string), both str subclasses, so `node[0] == 'symbol'` keeps working
while `dump()` can re-emit the original quoting faithfully.
"""

import re

_TOKEN_RE = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


class Atom(str):
    """A bare token (keyword / number / unquoted value).  Re-emitted as-is."""


class QStr(str):
    """A quoted string.  Re-emitted with quotes."""


def parse(text):
    stack = []
    cur = None
    for tok in _TOKEN_RE.finditer(text):
        t = tok.group(0)
        if t == '(':
            new = []
            if cur is not None:
                cur.append(new)
            stack.append(new)
            cur = new
        elif t == ')':
            if not stack:
                raise ValueError('unbalanced )')
            closed = stack.pop()
            if not stack:
                return closed
            cur = stack[-1]
        else:
            if cur is None:
                raise ValueError('atom outside list')
            cur.append(QStr(unquote(t)) if t[0] == '"' else Atom(t))
    raise ValueError('unbalanced (')


def unquote(tok):
    body = tok[1:-1]
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), body)


def quote(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def dump(node, indent=0):
    pad = '\t' * indent
    if isinstance(node, QStr):
        return quote(node)
    if isinstance(node, Atom):
        return str(node)
    if isinstance(node, (int, float)):
        return ('%g' % node)
    if isinstance(node, str):
        return quote(node)
    out = ['(']
    for i, child in enumerate(node):
        if i:
            out.append(' ' if not isinstance(child, list) else '\n' + pad + '\t')
        out.append(dump(child, indent + 1))
    out.append(')')
    return ''.join(out)


def find_all(node, tag):
    out = []
    _walk(node, tag, out)
    return out


def _walk(node, tag, out):
    if isinstance(node, list):
        if node and node[0] == tag:
            out.append(node)
        for c in node:
            _walk(c, tag, out)


def first(node, tag):
    if isinstance(node, list):
        for c in node:
            if isinstance(c, list) and c and c[0] == tag:
                return c
    return None


def child_value(node, tag, default=None):
    c = first(node, tag)
    if c is None or len(c) < 2:
        return default
    return c[1]
