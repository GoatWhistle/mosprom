import re

from cleanup_rules import AGENT_PERSON, TRACE, TRAILER


def clean_subject(message: bytes, subjects: dict[str, str]) -> bytes:
    text = message.decode('utf-8', 'replace').strip()
    subject = text.split('\n', 1)[0].strip() if text else ''
    subject = re.sub(r'^Merge pull request #\d+ from [^/\s]+/(\S+)', r"Merge branch '\1'", subject)
    subject = re.sub(r'\s*\(#\d+\)', '', subject)
    subject = re.sub(r'(^|\s)#\d+\b', r'\1', subject).strip()
    subject = subjects.get(subject, subject)
    if not subject or TRACE.search(subject):
        head = re.match(r'^([a-z]+)(\([^)]*\))?!?:', subject)
        subject = (head.group(1) if head else 'chore') + ': update project files'
    return (subject + '\n').encode()


def clean_person(name: bytes | None, email: bytes | None, human_name: bytes, human_email: bytes) -> tuple[bytes | None, bytes | None]:
    if AGENT_PERSON.search(((name or b'') + b' ' + (email or b'')).decode('utf-8', 'replace')):
        return human_name, human_email
    return name, email


def clean_tag(message: bytes) -> bytes:
    text = message.decode('utf-8', 'replace')
    kept = [line for line in text.splitlines() if not TRACE.search(line) and not TRAILER.search(line)]
    return ('\n'.join(kept).strip() + '\n').encode() if any(line.strip() for line in kept) else b'Release\n'
