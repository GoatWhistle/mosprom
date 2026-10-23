# Запуск и проверки

Главная часть — плагин STE Slicer: он сам ходит в LLM и MCP-серверы. Backend нужен только для Claude
по подписке: Compose поднимает один сервис без базы данных.

**Читайте, если** вы ставите плагин или запускаете backend · **Связано:** [архитектура](architecture.md) · [API](api.md)

## Как поставить плагин?

```bash
python3 plugin/build.py
```

Архив `plugin/dist/Brim-<версия>.zip` распакуйте в `%APPDATA%\steslicer\7.x\plugins` так, чтобы
получилось `plugins\Brim\plugin.json`, и перезапустите слайсер. В «Brim» → «Настройки» укажите URL
OpenAI-совместимого API (например, `https://host/v1`), модель и ключ. Подробно — `plugin/README.md`.

## Как запустить backend для Claude?

Нужны Docker и Compose v2. Из корня репозитория:

```bash
cp .env.example .env
LLM=true docker buildx bake
docker compose up
```

В настройках плагина: URL LLM — `http://<адрес машины с Compose>:8000/v1`, модель — `sonnet`, ключ —
OAuth-токен из `claude setup-token`. Порт публикуется только на `127.0.0.1`; для виртуальной машины
со слайсером пробросьте его или задайте другой адрес в Compose. Без `LLM=true` образ собирается без
`claude-agent-sdk` и отвечает 503.

Без Docker:

```bash
cd backend
uv sync
uv run uvicorn app.main:create_app --factory --reload
```

## Какие переменные читает backend?

| Переменная | По умолчанию | Что задаёт |
|---|---|---|
| `LLM_TIMEOUT_SECONDS` | `120` | Таймаут одного запроса к Claude |
| `BACKEND_PORT` | `8000` | Порт Compose |

Неверное число останавливает запуск с ошибкой, где названа переменная.

## Как проверить презентацию?

```bash
(cd presentation && npm ci && npm run build)
```

## Как проверить код?

```bash
cd plugin && PYTHONPATH=. python3 -B -m unittest discover -s tests -t .
cd backend && uv run ruff check . && uv run mypy . && uv run pytest tests/unit
```

Тесты плагина работают без слайсера: LLM — скриптовый HTTP-сервер, слайсер — заглушка.
Тесты backend подменяют Claude Agent SDK.

## Что делать, если не запускается?

| Симптом | Что проверить |
|---|---|
| Порт 8000 занят | Задайте свободный `BACKEND_PORT` в `.env` |
| `ConfigError` при старте | Значение переменной из сообщения |
| `No such image` при `docker compose up` | Образ не собран: `docker buildx bake` с теми же `COMPOSE_PROJECT_NAME` и `TAG` |
| 503 `model_failure` | Образ без `LLM=true`, неверный токен или Claude недоступен; причина — в журнале backend |
| Чат пишет «LLM is unreachable» | URL LLM недоступен из машины со слайсером |

---

<sub>[Оглавление документации](README.md) · [README проекта](../README.md)</sub>
