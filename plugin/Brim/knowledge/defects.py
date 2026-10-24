import json
import os

from ..execution.errors import OperationError
from ..protocol import constants
from .search import score

DEFECTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "defects.json")
MAX_RESULTS = 3
RELATIVE_CUTOFF = 0.5
ACTIVE_EXTRUDER = 0


def load_defects(path=DEFECTS_PATH):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)["defects"]


class DefectGuide(object):
    def __init__(self, facts, defects=None):
        self._facts = facts
        self._defects = defects if defects is not None else load_defects()

    def ids(self):
        return [item["id"] for item in self._defects]

    def lookup(self, query=None, defect_id=None):
        if defect_id:
            found = [item for item in self._defects if item["id"] == defect_id]
            if not found:
                raise OperationError(constants.ERR_INVALID_ARGUMENTS, "unknown defect %s; known: %s" % (
                    defect_id, ", ".join(self.ids())))
        elif query and query.strip():
            ranked = sorted(((score(query, item["names"] + [item["symptoms"]]), index, item)
                             for index, item in enumerate(self._defects)), key=lambda row: (-row[0], row[1]))
            best = ranked[0][0] if ranked else 0
            found = [item for value, _, item in ranked if value > 0 and value >= RELATIVE_CUTOFF * best][:MAX_RESULTS]
        else:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "query or defect_id required")
        unknown = []
        return {"defects": [self._with_values(item, unknown) for item in found], "unknown_keys": sorted(set(unknown)),
                "known_defects": [] if found else self.ids(),
                "values_from": "extruder %d stack (falls back to global values)" % ACTIVE_EXTRUDER,
                "note": "Steps are typical starting increments, not measured optima; change one or two settings per print."}

    def _with_values(self, defect, unknown):
        settings = []
        for item in defect["settings"]:
            try:
                facts = self._facts(item["key"], ACTIVE_EXTRUDER) or {}
            except Exception:
                facts = {}
            if not facts.get("known", facts.get("value") is not None):
                unknown.append(item["key"])
                continue
            row = dict(item, current=facts.get("value"))
            for name in ("minimum_value", "maximum_value", "minimum_value_warning", "maximum_value_warning"):
                if facts.get(name) is not None:
                    row[name] = facts[name]
            if facts.get("unit"):
                row["unit"] = facts["unit"]
            settings.append(row)
        return dict(defect, settings=settings)
