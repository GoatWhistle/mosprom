import io
import os
import re

from tests import support

WEB_DIR = os.path.join(support.PLUGIN_ROOT, "Brim", "web")
STYLES_DIR = os.path.join(WEB_DIR, "styles")
TOKENS_DIR = os.path.join(STYLES_DIR, "tokens")
EXEMPT_STYLES = (TOKENS_DIR + os.sep, os.path.join(STYLES_DIR, "fonts.css"))
CUSTOM_PROPERTY = re.compile(r"(--[\w-]+)\s*:")
VAR_CALL = re.compile(r"var\(\s*(--[\w-]+)\s*(,)?")
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{6})$")


def read(path):
    with io.open(path, encoding="utf-8") as handle:
        return handle.read()


def web_files(extension):
    found = []
    for folder, _, names in os.walk(WEB_DIR):
        for name in sorted(names):
            if name.endswith(extension):
                found.append(os.path.join(folder, name))
    return found


def component_styles():
    return [path for path in web_files(".css") if not path.startswith(EXEMPT_STYLES)]


def declarations(text):
    stack = []
    buffer = ""
    for char in text:
        if char == "{":
            stack.append(buffer.strip())
            buffer = ""
        elif char == "}":
            if buffer.strip():
                yield list(stack), buffer.strip()
            buffer = ""
            if stack:
                stack.pop()
        elif char == ";":
            if buffer.strip():
                yield list(stack), buffer.strip()
            buffer = ""
        else:
            buffer += char


def split_declaration(text):
    prop, _, value = text.partition(":")
    return prop.strip().lower(), value.strip()


def rules(text):
    for preludes, body in declarations(text):
        if ":" not in body or body.startswith("@"):
            continue
        prop, value = split_declaration(body)
        yield preludes, prop, value


def defined_properties():
    names = set()
    for path in web_files(".css") + web_files(".js"):
        names.update(CUSTOM_PROPERTY.findall(read(path)))
    return names


def theme_tables():
    text = read(os.path.join(TOKENS_DIR, "semantic.css"))
    tables = {}
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        theme = "dark" if 'data-theme="dark"' in selector else "light"
        tables[theme] = dict((name, value.strip()) for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body))
    return tables


def palette():
    text = read(os.path.join(TOKENS_DIR, "palette.css"))
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", text))


def resolve(name, table, colors):
    value = table.get(name)
    for _ in range(4):
        if value is None:
            return None
        match = re.match(r"^var\((--[\w-]+)\)$", value)
        if not match:
            break
        value = table.get(match.group(1)) or colors.get(match.group(1))
    return value if value and HEX_COLOR.match(value) else None


def luminance(value):
    channels = []
    for index in (1, 3, 5):
        channel = int(value[index:index + 2], 16) / 255.0
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first, second):
    a, b = luminance(first), luminance(second)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def css_classes():
    names = set()
    for path in web_files(".css"):
        names.update(re.findall(r"\.([a-z][a-z0-9-]*)", re.sub(r"url\([^)]*\)", "", read(path))))
    return names


def used_classes():
    found = []
    pattern = re.compile(r"class(?:Name)?\s*[:=]\s*[\"']([^\"']*)[\"']")
    for path in web_files(".js") + web_files(".html"):
        for literal in pattern.findall(read(path)):
            for word in literal.split():
                if re.match(r"^[a-z][a-z0-9-]*[a-z0-9]$", word):
                    found.append((os.path.relpath(path, WEB_DIR), word))
    return found
