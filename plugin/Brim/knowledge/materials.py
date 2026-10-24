import json
import os
import re

from ..execution.errors import OperationError
from ..protocol import constants

MATERIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "materials.json")
RESISTANCES = ("oil", "fuel", "alkali", "acid", "ipa", "water_hot", "uv", "ozone")
CONDUCTIVE_FILLER = re.compile(r"(?<![a-z])(cf|carbon|graphite|esd)(?![a-z])")
LOW_MOISTURE = ("very_low", "low")
GOOD_CREEP = ("good", "excellent")


def load_materials(path=MATERIALS_PATH):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _text(material):
    facts = material.get("facts") or {}
    return " ".join(str(item) for item in (facts.get("material"), facts.get("name"), facts.get("brand"),
                                           material.get("material_id")) if item).lower().replace("_", " ")


class MaterialMatcher(object):
    def __init__(self, read_state, data=None):
        self._read_state = read_state
        data = data if data is not None else load_materials()
        self._basis = data["basis"]
        self._ratings = data["ratings"]
        self._families = data["families"]
        aliases = [(alias, family) for family in self._families for alias in family["aliases"]]
        self._aliases = sorted(aliases, key=lambda pair: -len(pair[0]))

    def family_of(self, material):
        text = _text(material)
        for alias, family in self._aliases:
            if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(alias), text):
                conductive = family["conductive"] or bool(CONDUCTIVE_FILLER.search(text))
                return dict(family, conductive=conductive)
        return None

    def _good(self, rating):
        return self._ratings.index(rating) >= self._ratings.index("good")

    def evaluate(self, family, requirements):
        passes, fails = [], []

        def check(ok, name, detail):
            (passes if ok else fails).append("%s: %s" % (name, detail))

        if requirements.get("max_temp_c") is not None:
            check(family["max_service_c"] >= requirements["max_temp_c"], "max_temp_c",
                  "service up to %s °C, needed %s °C" % (family["max_service_c"], requirements["max_temp_c"]))
        if requirements.get("min_temp_c") is not None:
            check(family["min_service_c"] <= requirements["min_temp_c"], "min_temp_c",
                  "usable down to %s °C, needed %s °C" % (family["min_service_c"], requirements["min_temp_c"]))
        if requirements.get("max_density") is not None:
            check(family["density"] <= requirements["max_density"], "max_density",
                  "%s g/cm³, limit %s g/cm³" % (family["density"], requirements["max_density"]))
        if requirements.get("flexible") is not None:
            check(family["flexible"] == bool(requirements["flexible"]), "flexible",
                  "elastic" if family["flexible"] else "rigid")
        for name in requirements.get("resist") or []:
            rating = family["resistance"].get(name)
            if rating is None:
                continue
            check(self._good(rating), "resist_" + name, rating)
        if requirements.get("low_moisture"):
            check(family["moisture"] in LOW_MOISTURE, "low_moisture", "absorption %s" % family["moisture"])
        if requirements.get("low_friction"):
            check(family["low_friction"], "low_friction", "self-lubricating" if family["low_friction"] else "ordinary friction")
        if requirements.get("non_conductive"):
            check(not family["conductive"], "non_conductive", "conductive filler" if family["conductive"] else "dielectric")
        if requirements.get("creep_resistant"):
            check(family["creep"] in GOOD_CREEP, "creep_resistant", "creep %s" % family["creep"])
        return passes, fails

    def match(self, requirements):
        if not isinstance(requirements, dict) or not requirements:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "requirements must be a non-empty object")
        unknown = [name for name in requirements.get("resist") or [] if name not in RESISTANCES]
        state = self._read_state() or {}
        candidates, unmatched, covered, seen = [], [], set(), {}
        for material in state.get("available_materials") or []:
            if material.get("material_id") in seen:
                seen[material.get("material_id")].append(material.get("extruder"))
                continue
            extruders = seen[material.get("material_id")] = [material.get("extruder")]
            family = self.family_of(material)
            facts = material.get("facts") or {}
            if family is None:
                unmatched.append({"material_id": material.get("material_id"), "name": facts.get("name")})
                continue
            covered.add(family["id"])
            passes, fails = self.evaluate(family, requirements)
            candidates.append({"material_id": material.get("material_id"), "extruders": extruders,
                               "name": facts.get("name"), "brand": facts.get("brand"), "family": family["id"],
                               "passes": passes, "fails": fails, "notes": family["notes"],
                               "typical": dict((key, family[key]) for key in ("max_service_c", "min_service_c", "density",
                                                                               "moisture", "conductive"))})
        candidates.sort(key=lambda item: (len(item["fails"]), -len(item["passes"]), str(item["name"])))
        missing = []
        for family in self._families:
            if family["id"] not in covered and not self.evaluate(family, requirements)[1]:
                missing.append({"family": family["id"], "notes": family["notes"]})
        return {"candidates": candidates, "unmatched_materials": unmatched, "suitable_families_not_in_slicer": missing,
                "unknown_requirements": unknown, "basis": self._basis}
