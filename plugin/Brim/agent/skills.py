import os

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")
SKILL_FILE = "SKILL.md"
FIELDS = ("name", "order", "title_ru", "title_en", "description")


def parse_skill(text):
    meta = {}
    body = text
    if text.startswith("---"):
        header, separator, rest = text[3:].partition("\n---")
        if separator:
            body = rest.lstrip("\n")
            for line in header.splitlines():
                key, colon, value = line.partition(":")
                if colon and key.strip() in FIELDS:
                    meta[key.strip()] = value.strip()
    return meta, body.strip()


class SkillCatalog(object):
    def __init__(self, directory=SKILLS_DIR):
        self._skills = {}
        for name in sorted(os.listdir(directory)) if os.path.isdir(directory) else []:
            path = os.path.join(directory, name, SKILL_FILE)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                meta, body = parse_skill(handle.read())
            meta.setdefault("name", name)
            self._skills[meta["name"]] = dict(meta, body=body)
        self._order = sorted(self._skills, key=lambda key: (int(self._skills[key].get("order") or 99), key))

    def names(self):
        return list(self._order)

    def rows(self):
        return [dict((key, self._skills[name].get(key, "")) for key in FIELDS) for name in self._order]

    def body(self, name):
        skill = self._skills.get(name)
        return skill["body"] if skill is not None else None

    def catalog_text(self):
        return "\n".join("- %s: %s" % (name, self._skills[name].get("description", "")) for name in self._order)
