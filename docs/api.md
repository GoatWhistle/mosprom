# API и инструменты

У Brim три HTTP-контракта: локальный MCP плагина, локальный API браузерного чата и необязательный
backend для Claude. Порт MCP отличается от порта браузера. Оба локальных сервера запускает
сам плагин; их не нужно поднимать отдельной командой.

## Запросы к LLM

`plugin/Brim/agent/llm_client.py` вызывает `POST {base_url}/chat/completions` с `model`, `messages`
и `tools` в формате function calling. При заданном ключе добавляется `Authorization: Bearer …`.
Ожидается полный JSON с `choices[0].message`, текстом и/или `tool_calls`; стриминга нет.
`function.arguments` разбирается как JSON-объект. Таймаут клиента по умолчанию — 300 секунд.

Первое сообщение содержит инструкцию, текущую сцену, значения включённых настроек и выбранный
скилл. Изображения передаются в `image_url.url` как `data:<mime>;base64,…`. Документы читаются
инструментом, после чего их текст становится частью истории. `GET {base_url}/models` используется
кнопкой проверки соединения.

`ask_user` — инструмент самого цикла, отсутствующий в MCP-каталоге: `questions` содержит объекты
`{text, options?}`. Он приостанавливает выполнение до ответа `{"answer":"…"}`. Отказ от изменения
возвращает модели `rejected_by_user` и комментарий пользователя.

## Локальный MCP

Адрес и токен находятся в `<данные STE>/brim/mcp.json` в полях `url` и `token`.
Сервер слушает `127.0.0.1`, принимает `POST /mcp` с Bearer-токеном и JSON-RPC 2.0.
Запрос с `Origin`, неподходящим `Host` или неверным токеном получает HTTP 401.
Максимальное тело запроса — 1 MiB; превышение возвращает 413. GET возвращает 405.

Поддерживаются `initialize`, `ping`, `tools/list`, `tools/call`; уведомления не требуют ответа
и получают HTTP 202. Реализован протокол `2025-03-26`. В текущих исходниках `serverInfo.version`
остаётся `0.4.0`, хотя версия пакета в `plugin.json` — `0.5.2`; версию установки определяйте по
`plugin.json`.

Пример безопасного чтения через клиент, уже настроивший адрес и заголовок:

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"inspect_scene","arguments":{}}}
```

Успешный JSON-RPC-ответ содержит `result.content`: текстовый блок с сериализованным объектом
`{ok, result, error, applied}` и, при необходимости, блоки `image` с base64 и MIME-типом.
`result.isError` отражает неудачу инструмента. `applied` перечисляет уже выполненные операции.

Ошибки самого JSON-RPC: `-32700` — разбор JSON, `-32600` — форма запроса, `-32601` — метод,
`-32602` — параметры/имя инструмента, `-32603` — необработанная ошибка вызова.
Ошибка инструмента обычно приходит внутри успешного HTTP/JSON-RPC ответа с `isError: true`.
Коды включают `invalid_arguments`, `operation_failed`, `not_available`, `cancelled`,
`slice_failed`, `stale_result`, `outcome_unknown`.

Внешний MCP-клиент действует без UI-подтверждения и работает с текущей сценой/активным чатом.
Он должен исключать одновременные изменения со стороны человека или другого клиента.

## Каталог инструментов

Источник схем аргументов — [tools.json](../plugin/Brim/protocol/tools.json).

| Инструмент | Основные аргументы | Результат |
|---|---|---|
| `inspect_scene` | Нет | Принтер, режим, материалы, профиль, overrides, объекты, нарезка и ошибки |
| `inspect_profile` | Нет | Выбранный профиль, доступные качества и пользовательские профили |
| `inspect_material` | `material_id?` | Описание материала из слайсера |
| `search_settings` | `query` | До 25 совпадений: ключ, тип, единицы, границы, значение |
| `analyze_geometry` | `object_ids`, `direction?` | Габариты, площадь, топология, объём при допустимой сетке, нависания, ось 5D |
| `render_scene` | `view: "iso"` | Изометрический снимок; других видов сейчас нет |
| `apply_changes` | `operations`, `explanation?` | Применённые операции, `before` и состояние после |
| `slice` | Нет | Нарезка, оценки и пути G-code/3MF в текущем чате |
| `read_document` | `path`, `start?`, `max_chars?`, `sheet?`, `rows?`, `pages?` | Текст, предупреждения, `next_start`, встроенные изображения DOCX |
| `load_skill` | `name` | Инструкция выбранного скилла |
| `lookup_defect` | `query?`, `defect_id?` | Причины, ключи настроек, направления правок и `unknown_keys` |
| `match_materials` | `requirements` | Кандидаты из каталога, пройденные/непройденные условия и неизвестные семейства |
| `calculate` | `formula`, `inputs` | Значение, единицы, формула и допущения |
| `generate_calibration_model` | `kind`, `params?` | Путь STL и сведения о тесте; генерация сама не импортирует модель |
| `calibration_journal` | `action: "read"` или `"record"`, данные попытки | История и сравнение попыток одной геометрии |

`read_document` принимает путь вложения из папки текущего чата. По умолчанию возвращает
20 000 символов, максимум 60 000 за вызов; `next_start` задаёт продолжение.
`rows` и `pages` — включительные диапазоны `[first,last]`, начиная с 1.

Формулы: `gear_lewis_bending`, `hole_compensation`, `part_mass`, `rotating_hoop_stress`,
`shaft_torsion`, `thermal_expansion`. Их входы, единицы и ограничения указаны в схеме и результате.
Виды калибровки: `calibration_figure`, `cube`, `overhang_test`, `bridge_test`,
`stringing_towers`, `hole_tolerance`.

## Операции изменения сцены

Каждый элемент `operations` содержит `kind` и поля соответствующей операции:

| `kind` | Поля |
|---|---|
| `select_mode` | `mode`: `classic`, `cylindrical`, `cylindrical_full` |
| `select_profile` | `profile_id` из каталога |
| `select_material` | `material_id`, `extruder` |
| `set_global_setting` | `key`, `value` |
| `set_extruder_setting` | `key`, `value`, `extruder` |
| `reset_overrides` | `keys?`: без поля сбрасываются все overrides; пустой список ничего не сбрасывает |
| `import_model` | `path` |
| `open_3mf` | `path`, `import_as`: `restore_project` или `import_geometry` |
| `transform` | `object_id`, `frame: "scene"`, хотя бы одно из `position_mm`, `rotation_deg`, `scale`; при повороте `rotation_center` |
| `duplicate` | `object_id`, `count` |
| `arrange` | Необязательные `object_ids` |
| `delete` | `object_ids` |
| `set_object_extruder` | `object_id`, `extruder` |
| `save_profile` | `name` |

Координаты сцены: начало в центре стола, x вправо, y назад, z вверх; положение — центр габаритов.
Повороты X–Y–Z заданы в градусах относительно импортированной ориентации, масштаб — абсолютные
коэффициенты относительно исходного размера. Идентификаторы объектов и материалов берите из
состояния слайсера. Пакет не транзакционный: при ошибке учитывайте `applied`, не повторяйте его целиком.

## Внешние MCP-серверы

Плагин поддерживает Streamable HTTP с JSON и SSE в ответе, `Mcp-Session-Id`,
`MCP-Protocol-Version` и постраничным `tools/list`. Stdio-транспорта нет.
Пользователь задаёт имя, URL и один дополнительный заголовок. Имена инструментов преобразуются
в `<сервер>__<инструмент>`; конфликтующие имена скрываются с предупреждением.

## API браузерного чата

Меню открывает `http://127.0.0.1:<порт>/?token=<токен>`. SPA сохраняет токен в `sessionStorage`
и убирает его из адреса. Все `/api/*` требуют `X-Brim-Token` или параметр `token` и loopback `Host`.

| Метод | Вход | Ответ |
|---|---|---|
| `GET /api/view?since=<version>` | Последняя версия, опционально | `{version, view}`; long polling до 25 с |
| `POST /api/action` | `{name, args: [...]}` | `{result}`; действие из разрешённого списка |
| `POST /api/upload?name=<filename>` | Байты файла | `{path}`; файл прикрепляется контроллером |
| `GET /api/download?path=<path>` | Путь внутри данных Brim | Файл с `Content-Disposition` |
| `POST /api/open` | `{path}` внутри данных Brim | Открытие пути на машине слайсера |

Список действий и типы аргументов — `ACTIONS` в
[bridge.py](../plugin/Brim/browser/bridge.py). Например, отправка:
`{"name":"send","args":["Проверь текущую сцену"]}`. Режимы `setMode` — `ask` и `auto`.
Максимум JSON-тела — 1 MiB, загрузки — 100 MiB; прикрепление документа дополнительно ограничено
20 MiB и общими правилами вложений. Ответ upload сам по себе не подтверждает принятие вложения:
проверьте список вложений и notice в `view`.

Ошибки имеют вид `{"error":"…"}`: 400 неверные аргументы, 401 токен, 403 Host/путь,
404 неизвестное действие/файл, 413 размер, 503 интерфейс ещё запускается, 504 нет ответа Qt-потока.

## Необязательный Claude-прокси

| Метод | Поведение |
|---|---|
| `POST /v1/chat/completions` | Bearer OAuth-токен; преобразует сообщения и tools в вызов Claude; всегда модель `opus` |
| `GET /v1/models` | Без авторизации; список из `opus` |
| `GET /api/v1/health` | Без авторизации; `{"status":"ok"}`, только живость процесса |
| `GET /openapi.json`, `GET /docs` | OpenAPI и Swagger FastAPI |

Это подмножество Chat Completions: нет стриминга, выбор модели, `temperature`, `max_tokens`
и остальные дополнительные параметры не управляют текущим адаптером. Поддержаны роли
system/user/assistant/tool. Изображения — base64 data URL JPEG, PNG, GIF или WebP.
Схема OpenAPI описывает тело как JSON-объект; детальную валидацию выполняет `CompletionService`.

Ответ содержит `id`, `object: "chat.completion"`, `created`, `model`, `choices`,
`message.content` и при необходимости `message.tool_calls`. `usage` не предоставляется.
Ошибки — `{code, message}`: 401 отсутствие Bearer, 422 неверный ввод, 503 ошибка модели,
500 непредвиденная серверная ошибка. Пример: `{"code":"model_failure","message":"Language model failed"}`.

Зеркало запросов включается переменными из [инструкции запуска](running.md). Оно отправляет копию
валидного тела с заменой `model` и `stream: false`; Bearer-токен Claude туда не пересылается.
