import json

from Brim.agent import ask_user
from Brim.protocol import constants

COMMANDS = [
    ("вопрос", "карточка вопроса с вариантами"),
    ("подтверждение", "карточка подтверждения изменений"),
    ("результат", "слайсинг и карточка результата"),
    ("ошибка", "упавший инструмент и ошибка хода"),
    ("markdown", "длинный ответ с разметкой"),
    ("все", "всё подряд, в конце вопрос"),
]

GEAR_FILES = {"gcode": "C:/Brim/chats/demo/output/gear.gcode", "3mf": "C:/Brim/chats/demo/output/gear.3mf"}

MARKDOWN = (
    "## Что я поменял\n\n"
    "- **Высота слоя** 0,2 мм: модель низкая, скорость важнее мелких деталей.\n"
    "- **Заполнение** gyroid 25 %: зубьям нужна прочность во всех направлениях.\n"
    "- **Сопло** 240 °C, **стол** 80 °C — рабочий диапазон PETG.\n\n"
    "### Почему без поддержек\n\n"
    "Нависание справа 38°, это меньше порога 45°.\n\n"
    "```gcode\n; Brim · PETG\nG28\nM104 S240\nM140 S80\n```\n\n"
    "> Если первый слой не держится, поднимите стол на 5 °C."
)


def help_text():
    lines = ["Это песочница Brim: ответы скриптовые, слайсера нет. Напишите одну из команд:"]
    lines += ["- **%s** — %s" % (name, hint) for name, hint in COMMANDS]
    return "\n".join(lines)


def pick(text):
    value = (text or "").strip().lower()
    for name, _ in COMMANDS:
        if name in value:
            return name
    return "обычный"


class Steps(object):
    def __init__(self):
        self.items = []
        self.counter = 0

    def add(self, delay, action):
        self.items.append((delay, action))
        return self

    def think(self, delay=500):
        return self.add(delay, lambda turn: turn.emit("thinking"))

    def say(self, text, delay=700):
        return self.add(delay, lambda turn: turn.append({"role": "assistant", "content": text}))

    def tools(self, calls, delay=600, content=""):
        prepared = []
        for name, arguments in calls:
            self.counter += 1
            prepared.append({"id": "call%d" % self.counter, "type": "function",
                             "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}})
        self.add(delay, lambda turn: turn.append({"role": "assistant", "content": content, "tool_calls": prepared}))
        return [item["id"] for item in prepared]

    def result(self, call_id, payload, status="ok", delay=500):
        def apply(turn):
            turn.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(payload, ensure_ascii=False),
                         "brim_status": status, "brim_server": "brim"})
        return self.add(delay, apply)

    def error(self, message, delay=400):
        return self.add(delay, lambda turn: turn.emit("error", {"message": message}))

    def confirm(self, call_id, items, delay=400):
        return self.add(delay, lambda turn: turn.wait_confirm(call_id, items))

    def finish(self, delay=300):
        return self.add(delay, lambda turn: turn.emit("finished"))


def inspect(steps):
    ids = steps.tools([(constants.TOOL_INSPECT_SCENE, {"explanation": "Смотрю сцену"}),
                       (constants.TOOL_INSPECT_PROFILE, {"explanation": "Смотрю профиль"}),
                       (constants.TOOL_ANALYZE_GEOMETRY, {"explanation": "Ищу нависания"})],
                      content="Смотрю модель, профиль и геометрию.")
    steps.result(ids[0], {"objects": 1, "size_mm": [33, 33, 10]})
    steps.result(ids[1], {"profile": "classic", "layer_height": 0.2})
    steps.result(ids[2], {"overhang_deg": 38})
    return steps


def slice_run(steps):
    call = steps.tools([(constants.TOOL_SLICE, {"explanation": "Нарезаю"})], content="Нарезаю модель.")[0]
    steps.result(call, {"ok": True, "result": {"slice": {"print_time_seconds": 3180, "material_weight_g": [3.3]},
                                               "files": GEAR_FILES}}, delay=1400)
    return steps


def failure(steps):
    call = steps.tools([(constants.TOOL_RENDER_SCENE, {"explanation": "Делаю снимок сцены"})])[0]
    steps.result(call, {"error": {"code": "render_failed", "message": "Нет OpenGL-контекста"}}, status="failed")
    steps.error("Модель не ответила за 120 с. Проверьте адрес LLM в настройках.")
    return steps


def question(steps):
    steps.tools([(ask_user.NAME, {"questions": [
        {"text": "Под какую нагрузку деталь?", "options": ["Без нагрузки", "До 10 Н·м", "До 75 Н·м"]},
        {"text": "Какой пластик есть под рукой?", "options": ["PLA", "PETG", "Fiberpart PC G20"]}]})],
        content="Пара вопросов, чтобы подобрать материал.")
    return steps


def build(command):
    steps = Steps().think()
    if command == "вопрос":
        question(steps)
        return steps.finish()
    if command == "подтверждение":
        call = steps.tools([(constants.TOOL_APPLY_CHANGES, {"explanation": "Меняю профиль и материал"})],
                           content="Предлагаю такие изменения.")[0]
        steps.confirm(call, [
            {"kind": "select_profile", "target": "Профиль", "detail": "classic → fine 0,1 мм"},
            {"kind": "select_material", "target": "Материал", "detail": "PLA → PETG"},
            {"kind": "delete", "target": "Объект", "detail": "support_block.stl", "risky": True,
             "reason": "destructive"}])
        return steps
    if command == "результат":
        return slice_run(inspect(steps)).think().say("Готово: 0 ч 53 мин, 3,3 г PETG.").finish()
    if command == "ошибка":
        return failure(steps).finish()
    if command == "markdown":
        return steps.say(MARKDOWN).finish()
    if command == "все":
        inspect(steps).think().say(MARKDOWN)
        slice_run(steps)
        failure(steps)
        question(steps)
        return steps.finish()
    return inspect(steps).think().say("Шестерня 33×33×10 мм, PETG. Слой 0,2 мм, gyroid 25 %.\n\n" + help_text()).finish()


def after_answer():
    return Steps().think().say("Принял. Беру PETG и профиль classic: этого хватит под вашу нагрузку.").finish()


def after_decision(decision):
    text = "Применил изменения и нарезал заново." if decision == "approve" else "Ничего не меняю, оставляю как было."
    return Steps().think().say(text).finish()
