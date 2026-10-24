# Архитектура

> Агент и чат живут в плагине STE Slicer; backend — необязательный прокси к Claude по подписке.

## Что реализовано?

Решение — [ADR 0002](adr/0002-plugin-agent-openai-mcp-host.md); скиллы, документы и справочники — [ADR 0003](adr/0003-agent-skills-documents-knowledge.md).

```
Плагин STE Slicer (Python 3.5, PyQt5)
  окно чата ─► AgentLoop (фоновый поток)
                ├─ LlmClient: POST {URL LLM}/chat/completions ─► LLM организаторов
                │                                              └► backend /v1/chat/completions ─► Claude Agent SDK
                └─ McpHub: tools/list, tools/call
                     ├─ brim (встроенный, всегда включён)
                     └─ внешние серверы (Streamable HTTP)
  LocalMcpServer 127.0.0.1:<порт>/mcp — тот же диспетчер для внешних клиентов
  chats/<id>/ — chat.json, scene.3mf, files/, output/
```

| Часть | Где | Что делает |
|---|---|---|
| Цикл агента | `plugin/Brim/agent/` | Запрос к модели, исполнение инструментов, `ask_user`, подтверждения, лимит шагов, отмена |
| Инструменты слайсера | `plugin/Brim/execution/`, `plugin/Brim/slicer/` | Операции над сценой и настройками, слайсинг, экспорт G-code и 3MF |
| Чат | `plugin/Brim/chat/`, `plugin/Brim/ui/` | Лента из сообщений, карточки вопроса, подтверждения и результата, настройки и MCP-серверы |
| Проекты | `plugin/Brim/workspace/` | Папка на чат, атомарное сохранение сцены, переключение |
| Backend | `backend/` | Stateless `POST /v1/chat/completions` поверх Claude Agent SDK; БД нет |

Решения о печати принимает модель; код не подбирает параметры по правилам. Без настроенной LLM чат
отвечает явной ошибкой. Протоколы — [API](api.md).

---

<sub>[Оглавление документации](README.md) · [README проекта](../README.md)</sub>
