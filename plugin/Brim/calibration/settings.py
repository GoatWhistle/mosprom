ACTIVE_EXTRUDER = 0


def setting_facts(facts, key, extruder=None):
    if facts is None:
        return None
    try:
        found = facts(key, ACTIVE_EXTRUDER if extruder is None else extruder) or {}
    except Exception:
        found = {}
    return found if found.get("known", found.get("value") is not None) else None


def known_keys(facts, keys):
    if facts is None:
        return list(keys)
    return [key for key in keys if setting_facts(facts, key) is not None]
