def cell_text(value):
    return " ".join(str(value if value is not None else "").split()).replace("|", "\\|")


def markdown_table(rows):
    rows = [row for row in rows if any(cell_text(cell) for cell in row)]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    lines = []
    for index, row in enumerate(rows):
        cells = [cell_text(cell) for cell in row] + [""] * (width - len(row))
        lines.append("| %s |" % " | ".join(cells))
        if index == 0:
            lines.append("|%s" % ("---|" * width))
    return "\n".join(lines)
