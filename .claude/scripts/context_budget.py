import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = "context"
BUDGET = {
    "context/README.md": 6000,
    "context/SESSION.md": 6000,
    "context/open-questions.md": 3000,
}
ELSEWHERE = "organizer material to brief/, team artifacts to work/, decisions and product docs to docs/"


def worktree_files() -> dict[str, str]:
    base = ROOT / FOLDER
    if not base.is_dir():
        return {}
    return {
        path.relative_to(ROOT).as_posix(): path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.name != ".DS_Store"
    }


def staged_files() -> dict[str, str]:
    listing = subprocess.run(
        ["git", "ls-files", "--cached", "-z", "--", FOLDER],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.decode()
    files: dict[str, str] = {}
    for name in filter(None, listing.split("\0")):
        blob = subprocess.run(["git", "show", f":{name}"], cwd=ROOT, capture_output=True, check=True)
        files[name] = blob.stdout.decode("utf-8", errors="replace")
    return files


def protected_instructions(text: str) -> str:
    match = re.search(r"^## Explicit user instructions[ \t]*\n.*?(?=^## |\Z)", text, re.M | re.S)
    return match.group() if match else ""


def problems(files: dict[str, str]) -> list[str]:
    found = [f"{name}: required file is missing" for name in BUDGET if name not in files]
    for name, text in files.items():
        limit = BUDGET.get(name)
        protected = protected_instructions(text) if name == "context/SESSION.md" else ""
        mutable_size = len(text) - len(protected)
        if limit is None:
            found.append(f"{name}: not allowed in {FOLDER}/, move it: {ELSEWHERE}")
        elif len(text) > limit and (not protected or mutable_size > limit):
            found.append(f"{name}: mutable content {mutable_size} characters, budget {limit}; preserve explicit instructions")
    return found


def notices(files: dict[str, str]) -> list[str]:
    text = files.get("context/SESSION.md", "")
    protected = protected_instructions(text)
    if protected and len(text) > BUDGET["context/SESSION.md"] and len(text) - len(protected) <= BUDGET["context/SESSION.md"]:
        return ["SESSION target exceeded by protected user instructions; preserve them verbatim and continue."]
    return []


def usage(files: dict[str, str]) -> str:
    rows = [f"{name}: {len(files.get(name, ''))} / {limit}" for name, limit in BUDGET.items()]
    total = sum(len(files.get(name, "")) for name in BUDGET)
    rows.append(f"total: {total} / {sum(BUDGET.values())}")
    return "\n".join(rows)


def instruction(found: list[str]) -> str:
    return (
        f"{FOLDER}/ needs repair:\n  "
        + "\n  ".join(found)
        + "\nRun the compact-context skill now: move durable facts to their home, delete what is done,"
        " restore missing required files, then rerun python3 .claude/scripts/context_budget.py."
    )


def session_start() -> int:
    files = worktree_files()
    parts = [
        f"Project working memory, loaded from {FOLDER}/ at session start. It is the current state of the"
        " work; brief/, work/ and docs/ are reached through its links.",
    ]
    for name in BUDGET:
        if name in files:
            parts.append(f"===== {name} =====\n{files[name].rstrip()}")
    parts.extend(notices(files))
    found = problems(files)
    if found:
        parts.append(instruction(found))
    print("\n\n".join(parts))
    return 0


def stop(payload: str) -> int:
    try:
        event = json.loads(payload) if payload.strip() else {}
    except json.JSONDecodeError:
        event = {}
    if event.get("stop_hook_active"):
        return 0
    found = problems(worktree_files())
    if not found:
        return 0
    print(instruction(found), file=sys.stderr)
    return 2


def check(staged: bool) -> int:
    files = staged_files() if staged else worktree_files()
    found = problems(files)
    print(usage(files))
    for notice in notices(files):
        print(notice)
    if found:
        print("\n" + instruction(found), file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Keep {FOLDER}/ within its size budget")
    parser.add_argument("--staged", action="store_true", help="check the index instead of the working tree")
    parser.add_argument("--hook", choices=["session-start", "stop"], help="run as a Claude Code hook")
    args = parser.parse_args()
    if args.hook == "session-start":
        return session_start()
    if args.hook == "stop":
        return stop(sys.stdin.read())
    return check(args.staged)


if __name__ == "__main__":
    sys.exit(main())
