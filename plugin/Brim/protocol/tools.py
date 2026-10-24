import json
import os

TOOLS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools.json")


def load_tools(path=None):
    with open(path or TOOLS_PATH, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    items = raw.get("tools", []) if isinstance(raw, dict) else raw
    tools = []
    for item in items:
        schema = item.get("inputSchema", item.get("input_schema", item.get("parameters")))
        tool = {
            "name": item["name"],
            "description": item.get("description", ""),
            "inputSchema": schema or {"type": "object", "properties": {}},
        }
        if item.get("annotations"):
            tool["annotations"] = item["annotations"]
        tools.append(tool)
    return tools
