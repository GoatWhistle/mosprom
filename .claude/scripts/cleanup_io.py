import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from cleanup_rules import AGENT_DIRS, SKIP_DIRS, TEXT_LIMIT


def run(args: list[str], cwd: Path, check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        raise SystemExit(f"strip-ai: {' '.join(args[:3])} failed:\n{result.stderr.strip()}")
    return result.stdout


def read_text(path: Path) -> str | None:
    if path.is_symlink():
        return None
    try:
        if path.stat().st_size > TEXT_LIMIT:
            return None
        with open(path, encoding="utf-8", newline="") as fh:
            return fh.read()
    except (UnicodeDecodeError, OSError):
        return None


def write_text(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def walk(root: Path) -> tuple[list[str], list[str], list[str]]:
    files: list[str] = []
    dirs: list[str] = []
    agent_dirs: list[str] = []
    for current, subdirs, names in os.walk(root):
        rel = Path(current).relative_to(root).as_posix()
        prefix = "" if rel == "." else f"{rel}/"
        keep = []
        for d in subdirs:
            if d in SKIP_DIRS:
                continue
            if d in AGENT_DIRS:
                agent_dirs.append(prefix + d)
                continue
            if not (Path(current) / d).is_symlink():
                keep.append(d)
            else:
                names.append(d)
            dirs.append(prefix + d)
        subdirs[:] = keep
        files.extend(prefix + n for n in names)
    return files, dirs, agent_dirs


def scrub_lines(root: Path) -> list[str]:
    file = root / ".claude" / "scrub-paths"
    if not file.exists():
        return []
    patterns = [line.strip().rstrip("/") for line in file.read_text(encoding="utf-8").splitlines() if line.strip()]
    for pattern in patterns:
        if pattern.startswith("/") or ".." in pattern.split("/") or pattern in {".", ".git"}:
            raise SystemExit(f"strip-ai: unsafe scrub path: {pattern}")
    return patterns


def is_glob(pattern: str) -> bool:
    return any(c in pattern for c in "*?[")


def inside(path: str, targets: list[str]) -> bool:
    return any(path == t or path.startswith(t + "/") for t in targets)


def simulate(root: Path) -> Path:
    sim = Path(tempfile.mkdtemp(prefix="strip-ai-sim-"))
    listed, directories, _ = walk(root)
    for rel in directories:
        if not (root / rel).is_symlink():
            (sim / rel).mkdir(parents=True, exist_ok=True)
    for rel in listed:
        src = root / rel
        if src.is_symlink() or src.is_file():
            dest = sim / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest, follow_symlinks=False)
    return sim


def validate_paths(root: Path, targets: list[str], edits: dict[str, str]) -> None:
    base = root.resolve()
    for rel in [*targets, *edits]:
        path = root / rel
        if not path.parent.resolve().is_relative_to(base):
            raise SystemExit(f"strip-ai: refusing path outside repository: {rel}")
        if rel in edits and (path.is_symlink() or not path.resolve().is_relative_to(base)):
            raise SystemExit(f"strip-ai: refusing to rewrite symlink: {rel}")
