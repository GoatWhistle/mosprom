import fnmatch
import posixpath
import shutil
from pathlib import Path

from cleanup_io import inside, is_glob, read_text, validate_paths, walk, write_text
from cleanup_markdown import resolve, transform
from cleanup_rules import AGENT_FILES, AGENT_GLOBS, LINK, STYLE, STYLE_LISTS, TRACE


def find_targets(root: Path, extra: list[str]) -> list[str]:
    files, dirs, agent_dirs = walk(root)
    found = set(agent_dirs)
    for f in files:
        name = posixpath.basename(f)
        if name in AGENT_FILES or any(fnmatch.fnmatch(name, g) for g in AGENT_GLOBS):
            found.add(f)
    if (root / "context").is_dir():
        found.add("context")
    for pattern in extra:
        if is_glob(pattern):
            found.update(p for p in files + dirs if fnmatch.fnmatch(p, pattern))
        elif (root / pattern).exists():
            found.add(pattern)
    for d in sorted(dirs, key=lambda x: -x.count("/")):
        content = [f for f in files if f.startswith(d + "/")]
        if content and all(f in found or any(f.startswith(t + "/") for t in found) for f in content):
            found.add(d)
    ordered = sorted(found)
    return [p for p in ordered if not any(p.startswith(o + "/") for o in ordered if o != p)]


def plan_edits(root: Path, targets: list[str]) -> tuple[dict[str, str], list[str]]:
    files, _, _ = walk(root)
    edits: dict[str, str] = {}
    notes: list[str] = []
    for rel in files:
        if inside(rel, targets):
            continue
        text = read_text(root / rel)
        if text is None:
            continue
        new = transform(rel, text, targets, notes)
        if new != text:
            edits[rel] = new
    return edits, notes


def apply_cleanup(root: Path, targets: list[str], edits: dict[str, str]) -> None:
    validate_paths(root, targets, edits)
    for rel, text in edits.items():
        write_text(root / rel, text)
    for rel in targets:
        path = root / rel
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
        parent = path.parent
        while parent != root and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


def scan(root: Path) -> tuple[list[str], list[str], list[str]]:
    files, _, _ = walk(root)
    traces: list[str] = []
    style: list[str] = []
    broken: list[str] = []
    for rel in files:
        path = root / rel
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()) or not path.exists():
                broken.append(f"{rel}: external or dangling symlink, review manually")
            continue
        text = read_text(path)
        if text is None:
            continue
        for no, line in enumerate(text.splitlines(), 1):
            if TRACE.search(line):
                traces.append(f"{rel}:{no}: {line.strip()[:120]}")
        if (
            rel.endswith((".md", ".html", ".json"))
            and not STYLE_LISTS.search(rel)
            and (count := len(STYLE.findall(text)))
        ):
            style.append(f"{rel}: {count}")
        if rel.endswith(".md"):
            fence = False
            for no, line in enumerate(text.splitlines(), 1):
                if line.lstrip().startswith(("```", "~~~")):
                    fence = not fence
                    continue
                for m in [] if fence else LINK.finditer(line):
                    target = resolve(rel, m.group(3))
                    if target and not (root / target).exists():
                        broken.append(f"{rel}:{no}: {m.group(3)}")
    return traces, style, broken


def report_tree(traces: list[str], style: list[str], broken: list[str], notes: list[str]) -> bool:
    for title, items in (
        ("plain-text leftovers of removed links, reread", notes),
        ("AI-style wording to reread by hand (file: count)", style),
    ):
        if items:
            print(f"\n-- {title}:\n   " + "\n   ".join(items))
    clean = True
    for title, items in (("traces left, fix by hand", traces), ("broken links", broken)):
        if items:
            clean = False
            print(f"\n!! {title}:\n   " + "\n   ".join(items))
    if clean:
        print("\n== working tree: no AI traces, no broken links")
    return clean
