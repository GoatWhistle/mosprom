import json

ENCODINGS = ("utf-8-sig", "cp1251")


def decode(data):
    for encoding in ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def read_text(data):
    return {"text": decode(data)}


def read_json(data):
    text = decode(data)
    try:
        return {"text": json.dumps(json.loads(text), ensure_ascii=False, indent=2)}
    except ValueError:
        return {"text": text, "warnings": ["invalid JSON, shown as text"]}
