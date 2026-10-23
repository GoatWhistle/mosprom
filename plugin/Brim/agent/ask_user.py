import json

NAME = "ask_user"

DEFINITION = {
    "name": NAME,
    "description": ("Ask the user one or more questions and pause until they answer. Use it to interview the "
                    "user about requirements and to ask permission before unusual decisions. Offer options "
                    "when the answer is a choice. The user's reply arrives as this tool's result."),
    "parameters": {
        "type": "object",
        "required": ["questions"],
        "properties": {
            "questions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        },
    },
}


def questions_of(arguments):
    questions = []
    for item in (arguments or {}).get("questions") or []:
        if isinstance(item, str) and item.strip():
            questions.append({"text": item.strip(), "options": []})
        elif isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
            options = [str(option) for option in item.get("options") or [] if str(option).strip()]
            questions.append({"text": item["text"].strip(), "options": options})
    return questions


def answer_result(text):
    return json.dumps({"answer": text}, ensure_ascii=False)
