import re
from html import escape

CODE_BG = "#c0de01"
LINE = "#c0de02"
LINK = "#c0de03"
MUTED = "#c0de04"
MONO = "Consolas, 'DejaVu Sans Mono', monospace"
BLOCK_GAP = 8
CACHE_LIMIT = 512

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
ITEM = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$")
QUOTE = re.compile(r"^\s{0,3}>\s?(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
CODE_SPAN = re.compile(r"(`+)(.+?)\1")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
AUTO_LINK = re.compile(r"https?://(?:(?!&quot;|&#x27;|&gt;)[^\s<])+")
TRAILING = ".,;:!?)]"
BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*|(?<!\w)__(?=\S)(.+?)(?<=\S)__(?!\w)")
ITALIC = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])|(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])")
STRIKE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~")
TOKEN = re.compile("\x00(\\d+)\x00")
HEADING_SIZES = {1: 19, 2: 17, 3: 15}

_cache = {}


def _anchor(url, label):
    return '<a href="%s" style="color:%s">%s</a>' % (url, LINK, label)


def _auto_link(keep):
    def replace(match):
        url = match.group(0)
        tail = len(url)
        while tail > 0 and url[tail - 1] in TRAILING and not url[:tail].endswith("&amp;"):
            tail -= 1
        return keep(_anchor(url[:tail], url[:tail])) + url[tail:]
    return replace


def inline(text):
    stash = []

    def keep(markup):
        stash.append(markup)
        return "\x00%d\x00" % (len(stash) - 1)

    parts = []
    position = 0
    for match in CODE_SPAN.finditer(text):
        parts.append(escape(text[position:match.start()]))
        parts.append(keep('<code style="background-color:%s; font-family:%s">&nbsp;%s&nbsp;</code>'
                          % (CODE_BG, MONO, escape(match.group(2).strip()))))
        position = match.end()
    parts.append(escape(text[position:]))
    result = "".join(parts)
    result = LINK_RE.sub(lambda m: keep(_anchor(m.group(2), m.group(1))), result)
    result = AUTO_LINK.sub(_auto_link(keep), result)
    result = BOLD.sub(lambda m: "<b>%s</b>" % (m.group(1) or m.group(2)), result)
    result = ITALIC.sub(lambda m: "<i>%s</i>" % (m.group(1) or m.group(2)), result)
    result = STRIKE.sub(r"<s>\1</s>", result)
    while TOKEN.search(result):
        result = TOKEN.sub(lambda m: stash[int(m.group(1))], result)
    return result


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_table(lines, index):
    return "|" in lines[index] and index + 1 < len(lines) and "|" in lines[index + 1] \
        and TABLE_SEP.match(lines[index + 1]) is not None


def _table(lines, index, gap):
    aligns = []
    for cell in _cells(lines[index + 1]):
        right = cell.endswith(":")
        aligns.append("center" if right and cell.startswith(":") else "right" if right else "left")
    rows = ['<tr>%s</tr>' % "".join('<th align="%s">%s</th>' % (aligns[i] if i < len(aligns) else "left", inline(cell))
                                    for i, cell in enumerate(_cells(lines[index])))]
    index += 2
    while index < len(lines) and lines[index].strip() and "|" in lines[index]:
        rows.append('<tr>%s</tr>' % "".join('<td align="%s">%s</td>' % (aligns[i] if i < len(aligns) else "left",
                                                                         inline(cell))
                                            for i, cell in enumerate(_cells(lines[index]))))
        index += 1
    markup = ('<table border="1" cellspacing="0" cellpadding="4" style="margin-top:%dpx; border-color:%s; '
              'border-style:solid">%s</table>' % (gap, LINE, "".join(rows)))
    return markup, index


def _code(lines, index, gap):
    fence = FENCE.match(lines[index]).group(1)
    body = []
    index += 1
    while index < len(lines) and not lines[index].strip().startswith(fence):
        body.append(lines[index])
        index += 1
    markup = ('<table width="100%%" cellspacing="0" cellpadding="8" bgcolor="%s" style="margin-top:%dpx">'
              '<tr><td><pre style="font-family:%s; margin:0px">%s</pre></td></tr></table>'
              % (CODE_BG, gap, MONO, escape("\n".join(body))))
    return markup, index + 1


def _list(lines, index, gap):
    items = []
    while index < len(lines):
        match = ITEM.match(lines[index])
        if match:
            ordered = match.group(2)[0].isdigit()
            items.append([len(match.group(1).expandtabs(4)), "ol" if ordered else "ul", match.group(3)])
        elif lines[index].strip() and lines[index][:1].isspace() and items:
            items[-1][2] += "\n" + lines[index].strip()
        elif not lines[index].strip() and index + 1 < len(lines) and ITEM.match(lines[index + 1]):
            pass
        else:
            break
        index += 1
    out = []
    stack = []
    for indent, tag, text in items:
        while stack and indent < stack[-1][0]:
            out.append("</li></%s>" % stack.pop()[1])
        if stack and indent == stack[-1][0]:
            if tag == stack[-1][1]:
                out.append("</li>")
            else:
                out.append("</li></%s>" % stack.pop()[1])
        if not stack or indent > stack[-1][0]:
            top = gap if not out else 0
            out.append('<%s style="margin-top:%dpx; margin-bottom:0px">' % (tag, top))
            stack.append((indent, tag))
        out.append("<li>%s" % "<br>".join(inline(line) for line in text.split("\n")))
    while stack:
        out.append("</li></%s>" % stack.pop()[1])
    return "".join(out), index


def _starts_block(lines, index):
    line = lines[index]
    return bool(FENCE.match(line) or HEADING.match(line) or RULE.match(line) or ITEM.match(line)
                or QUOTE.match(line) or _is_table(lines, index))


def _block(lines, index, gap):
    line = lines[index]
    if FENCE.match(line):
        return _code(lines, index, gap)
    heading = HEADING.match(line)
    if heading:
        size = HEADING_SIZES.get(len(heading.group(1)), 14)
        return ('<p style="margin-top:%dpx; margin-bottom:0px; font-size:%dpx; font-weight:600">%s</p>'
                % (gap + 4 if gap else 0, size, inline(heading.group(2))), index + 1)
    if RULE.match(line):
        return '<hr style="margin-top:%dpx; color:%s">' % (gap, LINE), index + 1
    if _is_table(lines, index):
        return _table(lines, index, gap)
    if ITEM.match(line):
        return _list(lines, index, gap)
    if QUOTE.match(line):
        inner = []
        while index < len(lines) and QUOTE.match(lines[index]):
            inner.append(QUOTE.match(lines[index]).group(1))
            index += 1
        return ('<blockquote style="margin-top:%dpx; margin-left:12px; color:%s">%s</blockquote>'
                % (gap, MUTED, _render(inner)), index)
    paragraph = [line]
    index += 1
    while index < len(lines) and lines[index].strip() and not _starts_block(lines, index):
        paragraph.append(lines[index])
        index += 1
    return ('<p style="margin-top:%dpx; margin-bottom:0px">%s</p>'
            % (gap, "<br>".join(inline(item.strip()) for item in paragraph)), index)


def _render(lines):
    blocks = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        markup, index = _block(lines, index, BLOCK_GAP if blocks else 0)
        blocks.append(markup)
    return "".join(blocks)


def render(text):
    text = text or ""
    cached = _cache.get(text)
    if cached is None:
        if len(_cache) >= CACHE_LIMIT:
            _cache.clear()
        cached = _cache[text] = _render(text.replace("\r\n", "\n").split("\n"))
    return cached
