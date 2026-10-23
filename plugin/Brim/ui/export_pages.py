import html
import os
import re

from PyQt5.QtCore import QRectF, QSizeF
from PyQt5.QtGui import QColor, QImage, QPainter, QTextDocument

PAGE_WIDTH = 900
PAGE_HEIGHT = 1270
SCALE = 2
BACKGROUND = "#f6f5f2"
STYLE = """
body { color: #12130f; font-size: 15px; }
h1 { font-size: 24px; color: #12130f; }
h2 { font-size: 17px; color: #b83f0a; margin-top: 18px; }
code { font-family: Consolas, monospace; background-color: #ecebe7; }
blockquote { color: #615c56; margin-left: 12px; }
li { margin-bottom: 3px; }
p.meta { color: #615c56; font-size: 13px; }
"""
INLINE_CODE = re.compile(r"`([^`]+)`")
BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _inline(text):
    text = html.escape(text, quote=False)
    text = INLINE_CODE.sub(r"<code>\1</code>", text)
    return BOLD.sub(r"<b>\1</b>", text)


def markdown_html(markdown):
    parts = []
    depth = 0
    for index, line in enumerate(markdown.split("\n")):
        stripped = line.lstrip(" ")
        level = (len(line) - len(stripped)) // 2 + 1 if stripped.startswith("- ") else 0
        while depth > level:
            parts.append("</ul>")
            depth -= 1
        while depth < level:
            parts.append("<ul>")
            depth += 1
        if level:
            parts.append("<li>%s</li>" % _inline(stripped[2:]))
        elif stripped.startswith("> "):
            parts.append("<blockquote>%s</blockquote>" % _inline(stripped[2:]))
        elif line.startswith("## "):
            parts.append("<h2>%s</h2>" % _inline(line[3:]))
        elif line.startswith("# "):
            parts.append("<h1>%s</h1>" % _inline(line[2:]))
        elif line.strip():
            parts.append("<p%s>%s</p>" % (' class="meta"' if index == 2 else "", _inline(line)))
    parts.extend("</ul>" for _ in range(depth))
    return "<html><body>%s</body></html>" % "".join(parts)


def render_pages(markdown, folder):
    document = QTextDocument()
    document.setDefaultStyleSheet(STYLE)
    document.setDocumentMargin(36)
    document.setHtml(markdown_html(markdown))
    document.setPageSize(QSizeF(PAGE_WIDTH, PAGE_HEIGHT))
    count = document.pageCount()
    for page in range(count):
        image = QImage(PAGE_WIDTH * SCALE, PAGE_HEIGHT * SCALE, QImage.Format_ARGB32)
        image.fill(QColor(BACKGROUND))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.scale(SCALE, SCALE)
        painter.translate(0, -page * PAGE_HEIGHT)
        document.drawContents(painter, QRectF(0, page * PAGE_HEIGHT, PAGE_WIDTH, PAGE_HEIGHT))
        painter.end()
        image.save(os.path.join(folder, "chat_text_%02d.png" % (page + 1)))
    return count
