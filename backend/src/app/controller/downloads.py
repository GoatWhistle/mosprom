from urllib.parse import quote


def attachment_disposition(name: str) -> str:
    fallback = "".join(char if " " <= char <= "~" and char not in '"\\' else "_" for char in name)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"
