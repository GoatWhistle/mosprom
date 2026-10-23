from urllib.parse import quote


def attachment_disposition(name: str) -> str:
    fallback = name.encode("ascii", "replace").decode("ascii").replace('"', "_").replace("\\", "_")
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"
