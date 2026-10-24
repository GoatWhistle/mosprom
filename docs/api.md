# API

> Brim не держит своего API для чата: плагин STE Slicer сам вызывает OpenAI-совместимый
> `chat/completions` и MCP-серверы. Ниже — что плагин отдаёт наружу (локальный MCP) и что отвечает
> backend, нужный только для Claude по подписке. Спецификация backend генерируется из кода
> (`/openapi.json`, Swagger на `/docs`).

**Читайте, если** вы подключаете модель, MCP-сервер или внешнего клиента · **Связано:**
[архитектура](architecture.md) · [запуск](running.md)

---

## Что плагин отправляет модели?

`POST {URL LLM}/chat/completions` с `Authorization: Bearer <ключ>` (если задан), `model`, `messages`
и `tools` в формате OpenAI function calling. Ответ ждётся целиком, без стриминга. Первое сообщение —
системное: промпт и контекст сцены (принтер, режимы, профиль, материалы, объекты, вложения с
локальными путями, значения включённых настроек). Картинки идут частями `image_url` с data URL.

Инструменты: все инструменты встроенного MCP-сервера Brim без префикса, инструменты внешних серверов
как `<сервер>__<инструмент>` и встроенный `ask_user` (`questions: [{text, options?}]`). Результат
`ask_user` — ответ пользователя `{"answer": "..."}`; отказ в подтверждении —
`{"ok": false, "error": {"code": "rejected_by_user", "message": "..."}}`.

«Проверить соединение» вызывает `GET {URL LLM}/models`.

## Какие MCP-серверы подключает плагин?

Встроенный сервер Brim всегда включён. Свои серверы добавляются в настройках: имя, URL и один
заголовок (например, `Authorization: Bearer …`). Поддерживается транспорт Streamable HTTP: ответы
JSON и SSE, `Mcp-Session-Id`, `MCP-Protocol-Version`, постраничный `tools/list`. Недоступный сервер
пропускается с предупреждением.

## Что отдаёт локальный MCP плагина?

`POST http://127.0.0.1:<порт>/mcp` с `Authorization: Bearer <токен>`; адрес и токен — в
`<папка данных>\brim\mcp.json`. Методы `initialize`, `ping`, `tools/list`, `tools/call`. Запросы с
`Origin` или чужим `Host` отклоняются. Подтверждений нет: доступ ограничен loopback и токеном.

| Инструмент | Что делает | `readOnlyHint` |
|---|---|---|
| `search_settings` | Поиск настроек с типами, единицами, границами и значениями | да |
| `inspect_profile`, `inspect_material`, `inspect_scene` | Профиль, материал, состояние сцены | да |
| `analyze_geometry` | Числовой анализ сетки объектов | да |
| `render_scene` | Снимок сцены: текст и блок `image` (PNG) | да |
| `apply_changes` | Пакет операций: режим, профиль, материал, настройки, импорт по пути, трансформации | нет |
| `slice` | Слайсинг, G-code и 3MF в папку открытого чата | нет |

Результат — текстовый блок с JSON `{ok, result, error, applied}`, `isError` при неудаче.

## Что отвечает backend?

| Метод | Что делает |
|---|---|
| `POST /v1/chat/completions` | Запрос OpenAI → Claude Agent SDK. `Authorization: Bearer <OAuth-токен из claude setup-token>`, `model` игнорируется: всегда отвечает `opus`, и поле `model` ответа — `opus` |
| `GET /v1/models` | Одна модель — `opus` |
| `GET /api/v1/health` | Живость процесса |

Backend ничего не хранит и не логирует токен. Картинки принимаются только как data URL.

## Как выглядит ошибка backend?

```json
{
  "code": "model_failure",
  "message": "Language model failed"
}
```

| Статус | Когда |
|---|---|
| 401 | Нет Bearer-токена |
| 422 | Запрос не в формате OpenAI: нет `messages`, неизвестная роль, картинка не data URL |
| 503 | Claude недоступен, таймаут, некорректный ответ или образ собран без `LLM=true` |

---

<sub>[Оглавление документации](README.md) · [README проекта](../README.md)</sub>
