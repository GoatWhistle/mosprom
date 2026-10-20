import posixpath
import re

from cleanup_io import inside
from cleanup_rules import IGNORE_FILES, IGNORE_LINE, JSON_FILES, JSON_ITEM, LINK, LIST_ITEM, SCRUB_BLOCK, SEP_AFTER, SEP_BEFORE, SOURCE_RENAMES


def resolve(md: str, href: str) -> str | None:
    if "{{" in href or href.startswith(("#", "mailto:")) or "://" in href:
        return None
    target = href.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(md), target))
    return None if joined.startswith("..") else joined.strip("/")


def drop_links(md: str, text: str, targets: list[str], notes: list[str]) -> str:
    for m in reversed(
        [m for m in LINK.finditer(text) if (r := resolve(md, m.group(3))) and inside(r, targets)]
    ):
        before, after = text[: m.start()], text[m.end() :]
        sep_before, sep_after = SEP_BEFORE.search(before), SEP_AFTER.match(after)
        if sep_before:
            text = before[: sep_before.start()] + after
        elif sep_after:
            text = before + after[sep_after.end() :]
        else:
            text = before + ("" if m.group(1) else m.group(2)) + after
            if not m.group(1):
                notes.append(f"{md}: link to a removed page became plain text: «{m.group(2)}»")
    return text


def prune_markdown(md: str, text: str, targets: list[str], notes: list[str]) -> str:
    out: list[str] = []
    paragraph: list[str] = []
    fence = False

    def flush() -> None:
        if paragraph:
            joined = drop_links(md, "\n".join(paragraph), targets, notes)
            if joined.strip():
                out.extend(joined.split("\n"))
            paragraph.clear()

    for line in text.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            flush()
            fence = not fence
            out.append(line)
        elif fence:
            out.append(line)
        elif line.lstrip().startswith("|") or LIST_ITEM.match(line):
            flush()
            links = list(LINK.finditer(line))
            hits = [m for m in links if (r := resolve(md, m.group(3))) and inside(r, targets)]
            if hits and hits[0].start() == links[0].start():
                continue
            out.append(drop_links(md, line, targets, notes) if hits else line)
        elif not line.strip():
            flush()
            out.append(line)
        else:
            paragraph.append(line)
    flush()
    return "\n".join(out)


def transform(rel: str, text: str, targets: list[str], notes: list[str]) -> str:
    name = posixpath.basename(rel)
    for old, new in SOURCE_RENAMES.get(rel, {}).items():
        text = text.replace(old, new)
    if name in IGNORE_FILES:
        text = "".join(
            line for line in text.splitlines(keepends=True) if not IGNORE_LINE.search(line.rstrip("\r\n"))
        )
    if JSON_FILES.match(name):
        kept = "".join(
            line for line in text.splitlines(keepends=True) if not JSON_ITEM.match(line.rstrip("\r\n"))
        )
        text = re.sub(r",(\s*\])", r"\1", kept) if kept != text else text
    if "scrub:start" in text:
        text = SCRUB_BLOCK.sub("", text)
    if rel.endswith(".md"):
        text = prune_markdown(rel, text, targets, notes)
    return text
