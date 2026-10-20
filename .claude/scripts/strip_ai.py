import argparse
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from cleanup_history import history_report, rewrite_history
from cleanup_io import run, scrub_lines, simulate, validate_paths
from cleanup_tree import apply_cleanup, find_targets, plan_edits, report_tree, scan


def policy(root: Path) -> tuple[list[str], dict[str, str]]:
    path = root / '.claude/scrub-subjects.tsv'
    subjects = dict(line.split('\t', 1) for line in path.read_text(encoding='utf-8').splitlines() if '\t' in line) if path.exists() else {}
    return scrub_lines(root), subjects


def preview(root: Path, extra: list[str]) -> bool:
    sim = simulate(root)
    try:
        targets = find_targets(sim, extra)
        edits, notes = plan_edits(sim, targets)
        apply_cleanup(sim, targets, edits)
        return report_tree(*scan(sim), notes)
    finally:
        shutil.rmtree(sim, ignore_errors=True)


def export(root: Path, source: str, output: str | None) -> int:
    destination = Path(output).resolve() if output else Path(tempfile.mkdtemp(prefix='scrub-export-')) / 'scrub.git'
    if destination.exists():
        raise SystemExit(f'strip-ai: output already exists: {destination}')
    extra, subjects = policy(root)
    run(['git', 'clone', '--quiet', '--bare', source, str(destination)], root)
    for ref in run(['git', 'for-each-ref', '--format=%(refname)'], destination).splitlines():
        if not ref.startswith(('refs/heads/', 'refs/tags/')):
            run(['git', 'update-ref', '-d', ref], destination)
    rewrite_history(destination, extra, subjects)
    with tempfile.TemporaryDirectory(prefix='scrub-check-') as directory:
        run(['git', 'clone', '--quiet', str(destination), directory], root)
        if not report_tree(*scan(Path(directory)), []):
            raise SystemExit(f'strip-ai: exported tree verification failed: {destination}')
    print(f'\n== export verified: {destination}\nReview this copy before publishing; source history is unchanged.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog='strip-ai.sh', description='Clean internal files and attribution, with backups and verification.')
    parser.add_argument('--apply', action='store_true', help='clean working tree; default is a dry run')
    parser.add_argument('--history', action='store_true', help='with --apply: commit cleanup and rewrite history')
    parser.add_argument('--allow-dirty', action='store_true', help='allow uncommitted files with --apply, without --history')
    parser.add_argument('--export', nargs='+', metavar='PATH', help='create a cleaned bare copy: source [output]')
    args = parser.parse_args()
    root = Path(run(['git', 'rev-parse', '--show-toplevel'], Path.cwd()).strip())
    if args.export:
        if len(args.export) > 2 or args.apply or args.history or args.allow_dirty:
            parser.error('--export takes source [output] and cannot be combined with other options')
        return export(root, args.export[0], args.export[1] if len(args.export) == 2 else None)
    extra, subjects = policy(root)
    targets = find_targets(root, extra)
    edits, _ = plan_edits(root, targets)
    validate_paths(root, targets, edits)
    print(f'== remove ({len(targets)}):' + ''.join(f'\n   {t}' for t in targets))
    print(f'== edit ({len(edits)}):' + ''.join(f'\n   {e}' for e in edits))
    clean = preview(root, extra)
    if not args.apply:
        print('\n== dry run: repository untouched')
        history_report(root, extra)
        return 0 if clean else 1
    if not clean:
        raise SystemExit('strip-ai: preflight failed; repository untouched; fix the reported traces or links first')
    dirty = run(['git', 'status', '--porcelain'], root).strip()
    if dirty and (args.history or not args.allow_dirty):
        raise SystemExit('strip-ai: commit changes first, or use --allow-dirty without --history')
    backup = Path(tempfile.mkdtemp(prefix='strip-ai-backup-')) / 'files.tar.gz'
    with tarfile.open(backup, 'w:gz', dereference=False) as tar:
        for rel in [*targets, *edits]:
            if (root / rel).exists() or (root / rel).is_symlink():
                tar.add(root / rel, arcname=rel)
    print(f'\n== file backup: {backup}')
    edits, notes = plan_edits(root, targets)
    apply_cleanup(root, targets, edits)
    if run(['git', 'config', '--get', 'core.hooksPath'], root, check=False).strip().startswith('.claude/'):
        run(['git', 'config', '--unset', 'core.hooksPath'], root)
    if not report_tree(*scan(root), notes):
        raise SystemExit(f'strip-ai: tree verification failed; restore files from {backup}; history untouched')
    if args.history:
        if run(['git', 'status', '--porcelain'], root).strip():
            with tempfile.TemporaryDirectory(prefix='strip-ai-hooks-') as hooks:
                run(['git', 'add', '-A'], root)
                run(['git', '-c', f'core.hooksPath={hooks}', 'commit', '-q', '-m', 'chore: tidy repository'], root)
        rewrite_history(root, extra, subjects)
    print(f'\nRestore files: tar -xzf {backup} -C {root}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
