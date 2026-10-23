from urllib.parse import unquote

import pytest

from app.controller.downloads import attachment_disposition


def test_ascii_name_keeps_plain_filename() -> None:
    assert (
        attachment_disposition("part.stl")
        == "attachment; filename=\"part.stl\"; filename*=UTF-8''part.stl"
    )


def test_cyrillic_name_is_latin1_safe_and_recoverable() -> None:
    header = attachment_disposition("Шестерня.stl")
    header.encode("latin-1")
    assert unquote(header.split("filename*=UTF-8''", 1)[1]) == "Шестерня.stl"


@pytest.mark.parametrize("name", ['a"b.stl', "a\\b.stl", "a;b c.stl"])
def test_special_characters_do_not_break_header(name: str) -> None:
    header = attachment_disposition(name)
    fallback = header.split('filename="', 1)[1].split('"', 1)[0]
    assert '"' not in fallback and "\\" not in fallback
    assert unquote(header.split("filename*=UTF-8''", 1)[1]) == name
