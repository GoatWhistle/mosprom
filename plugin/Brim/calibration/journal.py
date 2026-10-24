import datetime
import json
import os

from ..execution.errors import OperationError
from ..protocol import constants
from ..workspace.store import _read_json, _write_json
from .figure import ZONES
from .settings import setting_facts

JOURNAL_NAME = "calibration.json"
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
VERDICTS = ("ok", "defect")
FIGURE_KIND = "calibration_figure"


def _invalid(message):
    raise OperationError(constants.ERR_INVALID_ARGUMENTS, message)


def _text(value, name, required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()):
        _invalid("%s must be a non-empty string" % name)
    return value


def _observations(items):
    if not isinstance(items, list):
        _invalid("observations must be a list")
    result = []
    for item in items:
        if not isinstance(item, dict) or item.get("verdict") not in VERDICTS:
            _invalid("each observation needs zone and verdict ok|defect")
        row = {"zone": _text(item.get("zone"), "zone", True), "verdict": item["verdict"]}
        for name in ("defect_id", "note"):
            if item.get(name) is not None:
                row[name] = _text(item[name], name)
        result.append(row)
    return result


def _setting_name(key, extruder):
    return key if extruder is None else "%s@%d" % (key, extruder)


def _changes(items, facts):
    if items is None:
        return []
    if not isinstance(items, list):
        _invalid("changes must be a list")
    result = []
    for item in items:
        extruder = item.get("extruder") if isinstance(item, dict) else None
        if not isinstance(item, dict) or "after" not in item or (
                extruder is not None and (isinstance(extruder, bool) or not isinstance(extruder, int))):
            _invalid("each change needs key, after and an optional integer extruder")
        key = _text(item.get("key"), "key", True)
        current = setting_facts(facts, key, extruder)
        result.append({"key": key, "extruder": extruder, "before": current.get("value") if current else None,
                       "after": item["after"], "reason": _text(item.get("reason"), "reason")})
    return result


def _snapshot(facts, changes):
    pairs = [(key, None) for zone in ZONES for key in zone["setting_keys"]]
    pairs += [(change["key"], change["extruder"]) for change in changes]
    values = {}
    for key, extruder in pairs:
        current = setting_facts(facts, key, extruder)
        if current is not None:
            values[_setting_name(key, extruder)] = current.get("value")
    return values


def _new_photos(directory, attempts):
    seen = set(name for attempt in attempts for name in attempt.get("photos", []))
    names = os.listdir(directory) if os.path.isdir(directory) else []
    return sorted(name for name in names if name not in seen and os.path.isfile(os.path.join(directory, name))
                  and (name.startswith("image-") or name.lower().endswith(IMAGE_SUFFIXES)))


def _geometry(attempt):
    return json.dumps([attempt["kind"], attempt["params"]], sort_keys=True)


def _defects(attempt):
    found = {}
    for item in attempt["observations"]:
        if item["verdict"] == "defect":
            found.setdefault(item["zone"], set()).add(item.get("defect_id") or "defect")
    return found


def _compare(previous, latest):
    before, after = _defects(previous), _defects(latest)
    zones = {"fixed": [], "persists": [], "new": []}
    for zone in sorted(set(before) | set(after)):
        if zone in before and zone not in after:
            zones["fixed"].append({"zone": zone, "defect_ids": sorted(before[zone])})
        elif zone in before:
            zones["persists"].append({"zone": zone, "defect_ids": sorted(after[zone])})
        else:
            zones["new"].append({"zone": zone, "defect_ids": sorted(after[zone])})
    old, new = previous["printed_with"], latest["printed_with"]
    changed = [{"key": key, "before": old.get(key), "after": new.get(key)}
               for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)]
    return dict(zones, attempt=latest["attempt"], compared_with=previous["attempt"], settings_changed=changed)


class CalibrationJournal(object):
    def __init__(self, directory, facts):
        if directory is None:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "no chat is open to keep the calibration journal")
        self._directory = directory
        self._facts = facts
        self._path = os.path.join(directory, JOURNAL_NAME)

    def attempts(self):
        data = _read_json(self._path) or {}
        return data.get("attempts") if isinstance(data.get("attempts"), list) else []

    def record(self, arguments):
        attempts = self.attempts()
        kind = _text(arguments.get("kind"), "kind", True)
        params = {} if kind == FIGURE_KIND else arguments.get("params") or {}
        if not isinstance(params, dict):
            _invalid("params must be an object")
        changes = _changes(arguments.get("changes"), self._facts)
        attempt = {"attempt": len(attempts) + 1, "recorded_at": datetime.datetime.now().isoformat(),
                   "kind": kind, "params": params,
                   "figure_path": _text(arguments.get("figure_path"), "figure_path"),
                   "observations": _observations(arguments.get("observations")),
                   "printed_with": _snapshot(self._facts, changes), "changes": changes,
                   "lesson": _text(arguments.get("lesson"), "lesson"),
                   "photos": _new_photos(self._directory, attempts)}
        os.makedirs(self._directory, exist_ok=True)
        _write_json(self._path, {"attempts": attempts + [attempt]})
        return {"recorded": attempt, "next_step": "apply the planned changes with apply_changes, then print again"}

    def read(self):
        attempts = self.attempts()
        comparison = None
        other = []
        if attempts:
            latest = attempts[-1]
            same = [item for item in attempts[:-1] if _geometry(item) == _geometry(latest)]
            comparison = _compare(same[-1], latest) if same else None
            other = [item["attempt"] for item in attempts if _geometry(item) != _geometry(latest)]
        return {"attempts": attempts, "comparison": comparison, "other_geometry_attempts": other,
                "note": "Only attempts with the same kind and params are compared; printed_with is the settings "
                        "snapshot taken when the attempt was recorded, before its planned changes."}


def run_journal(arguments, directory, facts):
    journal = CalibrationJournal(directory, facts)
    action = arguments.get("action")
    if action == "record":
        return journal.record(arguments)
    if action == "read":
        return journal.read()
    _invalid("action must be record or read")
