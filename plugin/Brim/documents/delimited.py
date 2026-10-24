import csv
import io

from .tables import markdown_table
from .text import decode

SNIFF_CHARS = 8192
DELIMITERS = ",;\t|"


def _delimiter(sample):
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        count, delimiter = max((sample.count(item), item) for item in DELIMITERS)
        return delimiter if count else ","


def select_rows(table, rows):
    if not rows:
        return table
    first, last = rows
    return table[:1] + table[max(first, 2) - 1:last]


def read_delimited(data, rows=None):
    text = decode(data)
    delimiter = _delimiter(text[:SNIFF_CHARS])
    table = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    return {"text": markdown_table(select_rows(table, rows)), "rows": len(table), "delimiter": delimiter}
