# Запуск и проверки

Compose запускает PostgreSQL 16, одноразовую миграцию dbmate и бэкенд. Отдельного веб-фронтенда нет;
встроенный чат STE Slicer пишется отдельно и в этом репозитории не реализован.

**Читайте, если** вы запускаете бэкенд · **Связано:** [архитектура](architecture.md) · [API](api.md)

## Как запустить через Docker?

Нужны Docker и Compose v2. Из корня репозитория:

```bash
cp .env.example .env
docker buildx bake
docker compose up
```

API: http://localhost:8000, Swagger: http://localhost:8000/docs. Образ бэкенда собирает только
`docker-bake.hcl`; Compose не скачивает его из реестра, поэтому без сборки `docker compose up`
остановится с ошибкой. Порядок старта: `db` → `migrate` (разово) → `backend`. Данные лежат в
томе `db-data` и переживают `docker compose down`; `down -v` их удаляет. Порт PostgreSQL наружу не
публикуется.

## Как разрабатывать без Docker?

Нужны Python 3.12+, uv и PostgreSQL с применёнными миграциями:

```bash
cd backend
uv sync
DATABASE_URL=postgresql://brim:brim@localhost:5432/brim uv run uvicorn app.main:create_app --factory --reload
```

## Какие переменные читает бэкенд?

| Переменная | По умолчанию | Что задаёт |
|---|---|---|
| `DATABASE_URL` | в Compose собирается из `POSTGRES_*` | DSN PostgreSQL; без него бэкенд не стартует |
| `DB_POOL_MAX_SIZE` | `10` | Размер пула соединений |
| `LLM_TIMEOUT_SECONDS` | `120` | Таймаут запроса к LLM |
| `CORRECTION_LIMIT` | `3` | Подряд неудачных исправлений одной операции до просьбы о помощи |
| `AGENT_MAX_STEPS` | `60` | Предел шагов агента в запуске |
| `TOOL_TIMEOUT_SECONDS`, `SLICE_TIMEOUT_SECONDS`, `SAVE_TIMEOUT_SECONDS` | `120`, `900`, `300` | Ожидание инструмента, слайсинга и сохранения файлов |
| `BACKEND_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `8000`, `brim`, `brim`, `brim` | Параметры Compose |

URL, модель и ключ LLM переменными не задаются: их передаёт плагин методом `PUT /instances/llm`.
Неверное число останавливает запуск с ошибкой, где названа переменная.

## Как проверить презентацию?

Из корня, каждую команду отдельно:

```bash
(cd presentation && npm ci && npm run build)
```

## Как проверить бэкенд?

Нужен [uv](https://docs.astral.sh/uv/). Из корня:

```bash
cd backend
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest tests/unit
uv run pytest tests/integration
```

`tests/unit` работает без базы и сети. `tests/integration` сам поднимает PostgreSQL 16 в Docker и
применяет миграции образом dbmate; без запущенного Docker тесты падают с понятным сообщением. LLM
в e2e-тестах скриптован, плагин изображает WebSocket-клиент: это проверка протокола, а не
интеграции с настоящим STE Slicer.

## Что делать, если не запускается?

| Симптом | Что проверить |
|---|---|
| Порт 8000 занят | Задайте свободный `BACKEND_PORT` в `.env` |
| `ConfigError` при старте | Значение переменной из сообщения |
| Бэкенд `unhealthy`, `Permission denied` в логах | У файлов в `backend/src` нет права чтения для всех (`chmod -R go+rX backend/src`), затем пересоберите образ |
| `No such image` при `docker compose up` | Образы не собраны: `docker buildx bake` с теми же `COMPOSE_PROJECT_NAME` и `TAG` |
| 409 `llm_not_configured` или запуск `failed` | Плагин не передал ключ: `PUT /api/v1/instances/llm` |

---

<sub>[Оглавление документации](README.md) · [README проекта](../README.md)</sub>
