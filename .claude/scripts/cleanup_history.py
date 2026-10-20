import fnmatch
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from cleanup_io import is_glob, run
from cleanup_rules import AGENT_DIRS, AGENT_FILES, AGENT_GLOBS, AGENT_PERSON, TRACE, TRAILER

LEGACY_PATHS = ["docs/screens", "docs/audits", "docs/research", "presentation/QA.md", "presentation/evidence.md"]


def agent_path(path: str, extra: list[str]) -> bool:
    parts = path.split('/')
    return (
        any(p in AGENT_DIRS for p in parts[:-1])
        or parts[-1] in AGENT_FILES
        or any(fnmatch.fnmatch(parts[-1], g) for g in AGENT_GLOBS)
        or path.startswith('context/')
        or any(fnmatch.fnmatch(path, e) if is_glob(e) else path == e or path.startswith(e + '/') for e in extra)
    )


def history_report(root: Path, extra: list[str]) -> int:
    extra = [*extra, *LEGACY_PATHS]
    log = run(['git', 'log', '--all', '--format=%h%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%s%x1f%b%x1e'], root)
    commits = [c.strip('\n').split('\x1f') for c in log.split('\x1e') if c.strip()]
    issues = {
        'commit bodies': [c[0] for c in commits if c[6].strip()],
        'commit trailers': [c[0] for c in commits if TRAILER.search(c[6])],
        'agent authors': [c[0] for c in commits if AGENT_PERSON.search(' '.join(c[1:5]))],
        'subjects with issue numbers or agents': [c[0] for c in commits if TRACE.search(c[5]) or re.search(r'(^|\s|\()#\d+', c[5])],
    }
    names = run(['git', 'log', '--all', '--format=', '--name-only'], root).splitlines()
    issues['internal paths'] = sorted({p for p in names if agent_path(p, extra)})
    tags = run(['git', 'for-each-ref', '--format=%(refname)%1f%(taggername)%1f%(taggeremail)%1f%(contents)%1e', 'refs/tags'], root)
    issues['annotated tag traces'] = [row.split('\x1f')[0] for row in tags.split('\x1e') if TRACE.search(row) or AGENT_PERSON.search(' '.join(row.split('\x1f')[1:3])) or TRAILER.search(row)]
    print(f'\n== history: {len(commits)} commits')
    for title, items in issues.items():
        print(f"   {'!!' if items else 'ok'} {title}: {len(items)}" + ''.join(f'\n        {i}' for i in items[:5]))
    return sum(map(len, issues.values()))


def verify_blobs(root: Path) -> int:
    objects = dict(row.split(" ", 1) if " " in row else (row, "") for row in run(["git", "rev-list", "--objects", "--all"], root).splitlines())
    listing = subprocess.run(["git", "cat-file", "--batch-check"], cwd=root, input="\n".join(objects).encode(), capture_output=True, check=True).stdout
    blobs = [row.split()[0] for row in listing.splitlines() if row.split()[1] == b"blob"]
    data = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input=b"\n".join(blobs), capture_output=True, check=True).stdout
    offset = 0
    hits = []
    for oid in blobs:
        end = data.index(b"\n", offset)
        size = int(data[offset:end].split()[2])
        raw = data[end + 1:end + 1 + size]
        offset = end + size + 2
        if b"\0" in raw:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if TRACE.search(text):
            hits.append(f"{oid.decode()[:12]} {objects.get(oid.decode(), '')}")
    if hits:
        print("\n!! traces in historical content:\n   " + "\n   ".join(hits[:20]))
    return len(hits)


def filter_repo_command(root: Path) -> list[str]:
    if subprocess.run(['git', 'filter-repo', '--version'], cwd=root, capture_output=True).returncode == 0:
        return ['git', 'filter-repo']
    if shutil.which('uvx'):
        return ['uvx', 'git-filter-repo']
    raise SystemExit('strip-ai: history cleanup needs git-filter-repo or uvx')


def callbacks(root: Path, extra: list[str], subjects: dict[str, str], name: str, email: str) -> tuple[str, str, str]:
    paths = run(['git', 'log', '--all', '--format=', '--name-only'], root).splitlines()
    targets = {p for p in paths if agent_path(p, extra)}
    directories = {str(parent) for p in paths if p for parent in Path(p).parents if str(parent) != '.'}
    for directory in directories:
        content = {p for p in paths if p.startswith(directory + '/')}
        if content and content <= targets:
            targets.add(directory)
    targets = sorted(targets)
    prelude = f"import sys\nsys.path.insert(0, {str(Path(__file__).resolve().parent)!r})\n"
    commit = prelude + f"from cleanup_messages import clean_subject, clean_person\ncommit.message = clean_subject(commit.message, {subjects!r})\ncommit.author_name, commit.author_email = clean_person(commit.author_name, commit.author_email, {name.encode()!r}, {email.encode()!r})\ncommit.committer_name, commit.committer_email = clean_person(commit.committer_name, commit.committer_email, {name.encode()!r}, {email.encode()!r})\n"
    tag = prelude + f"from cleanup_messages import clean_tag, clean_person\ntag.message = clean_tag(tag.message)\ntag.tagger_name, tag.tagger_email = clean_person(tag.tagger_name, tag.tagger_email, {name.encode()!r}, {email.encode()!r})\n"
    blob = prelude + f'''from cleanup_markdown import transform
from cleanup_rules import TEXT_LIMIT
if mode not in (b'100644', b'100755') or value.get_size_by_identifier(blob_id) > TEXT_LIMIT:
    return (filename, mode, blob_id)
key = (filename, blob_id)
if key not in value.data:
    raw = value.get_contents_by_identifier(blob_id)
    if value.is_binary(raw):
        value.data[key] = blob_id
    else:
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            value.data[key] = blob_id
        else:
            cleaned = transform(filename.decode('utf-8'), text, {targets!r}, [])
            value.data[key] = value.insert_file_with_contents(cleaned.encode()) if cleaned != text else blob_id
return (filename, mode, value.data[key])
'''
    return commit, tag, blob


def rewrite_history(root: Path, extra: list[str], subjects: dict[str, str]) -> None:
    extra = [*extra, *LEGACY_PATHS]
    name = run(['git', 'config', 'user.name'], root, check=False).strip()
    email = run(['git', 'config', 'user.email'], root, check=False).strip()
    if not name or not email or AGENT_PERSON.search(name + ' ' + email):
        raise SystemExit('strip-ai: configure a human git user.name and user.email before rewriting history')
    command = filter_repo_command(root)
    backup_dir = Path(tempfile.mkdtemp(prefix='strip-ai-history-'))
    bundle = backup_dir / 'original.bundle'
    run(['git', 'bundle', 'create', str(bundle), '--all'], root)
    print(f'\n== history backup: {bundle}')
    remotes = {line.split()[0]: line.split()[1] for line in run(['git', 'remote', '-v'], root).splitlines() if line.endswith('(fetch)')}
    paths = ['--path', 'context/']
    for d in AGENT_DIRS:
        paths += ['--path', d, '--path-glob', f'*/{d}/*']
    for f in AGENT_FILES:
        paths += ['--path', f, '--path-glob', f'*/{f}']
    for g in AGENT_GLOBS:
        paths += ['--path-glob', f'*{g}']
    for e in extra:
        paths += ['--path-glob', e] if is_glob(e) else ['--path', e]
    commit, tag, blob = callbacks(root, extra, subjects, name, email)
    run([*command, '--force', '--invert-paths', *paths, '--commit-callback', commit, '--tag-callback', tag, '--file-info-callback', blob], root)
    for remote, url in remotes.items():
        if remote not in run(['git', 'remote'], root).split():
            run(['git', 'remote', 'add', remote, url], root)
    if run(['git', 'rev-parse', '--is-bare-repository'], root).strip() == 'false':
        run(['git', 'reset', '--hard', '-q'], root)
    issues = history_report(root, extra) + verify_blobs(root)
    if issues:
        raise SystemExit(f'strip-ai: history verification failed; backup: {bundle}; nothing pushed')
    print('== history verified: subjects only, clean authors, tags and historical content')
    print(f"   restore refs: git fetch {bundle} '+refs/*:refs/*'")
