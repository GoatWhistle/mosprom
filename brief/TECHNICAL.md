# Полное техническое задание с сайта организаторов

Источник: https://665dc1hack2026.k8s.stereotech.cloud/#case, получено 2026-10-23.
Текст раздела «Описание кейса» сохранён дословно; HTML-разметка преобразована в текст.
Номера разделов соответствуют сайту. Код — цитата организаторов, не код проекта.
Исходный HTML-фрагмент: [снимок](sources/official-case-2026-10-23.html).
Это дополнение к PDF; дата публикации страницы неизвестна.

1. Проблема

В современных слайсерах больше 100 параметров печати: температуры, скорости, высота слоя, заполнение, поддержки, ретракт, охлаждение, адгезия. Подбирать режимы умеет опытный инженер, а новичку это сделать трудно. Без интеллектуального помощника на ручную настройку уходят часы, а на пробные печати — материал.

Второстепенные проблемы:

Слайсер сложно освоить новичку.

Пробные печати тратят материал и время.

Нет единой точки входа: модель → настройка → G-code.

При смене материала или задачи всё приходится настраивать заново.

2. Задача

Разработать плагин для STE Slicer (слайсер Stereotech, глубокий форк Cura 3.6, LGPLv3). Плагин добавляет в слайсер окно чатбота. Пользователь описывает задачу текстом и прикладывает изображения или 3D-модели, а LLM через MCP-инструменты:

выбирает режим печати (3D или 5D), профиль, материал и настройки;

загружает, ориентирует и расставляет модели;

запускает слайсинг и объясняет пользователю, какие решения приняла.

Пример: пользователь пишет «Кронштейн под нагрузку, PETG, без поддержек» и прикладывает STL. На выходе он получает настроенный проект, G-code и объяснение выбранных параметров.

3. Технические требования

3.1. Стек

Python + PyQt5, версии те же, что в выданном дистрибутиве STE Slicer (Python 3.5-совместимый код).

Плагин в формате STE Slicer (Cura 3.6): plugin.json с "api": 5, см. раздел 4.

Интерфейс чатбота — SPA на HTML + CSS + JS, без серверного рендеринга.

3.2. Окно чатбота

Плагин поднимает локальный HTTP-сервер (при необходимости — WebSocket) и открывает SPA в системном браузере на http://localhost:<port>. Связь JS ↔ Python идёт через этот сервер: fetch для запросов, WebSocket или polling для потоковых событий (ответ модели, прогресс слайсинга).

Обязательные функции:

история диалога и ввод текста;

прикрепление изображений (JPG/PNG) и 3D-моделей (STL/OBJ/3MF);

отображение вызовов инструментов и их результатов (пользователю видно, что меняет агент);

статус и прогресс слайсинга, итог (время печати, расход материала).

3.3. Подключение к LLM

URL и ключ доступа выдают организаторы.

Поддерживается только OpenAI-совместимый API: Chat Completions с tool calling, изображения передаются как image_url (base64).

Ключ нельзя хардкодить в исходниках: он вводится в настройках плагина и хранится в настройках приложения.

3.4. MCP-инструменты

Плагин реализует MCP-сервер (JSON-RPC: tools/list, tools/call) поверх API слайсера. Эти же инструменты агент передаёт в LLM как tools. Названия и схемы аргументов команда выбирает сама. Минимальный набор:

 | Группа
 | Инструменты

 | Настройки и профили
 | прочитать/изменить настройку (глобальную и экструдера); список профилей качества и материалов; выбор, создание и сохранение профиля; переключение режима печати 3D ↔ 5D

 | Модели
 | загрузить файл в сцену; список объектов; перемещение, поворот, масштаб; авто-расстановка; удаление; габариты модели

 | Слайсинг
 | запустить слайсинг; статус и прогресс; результат (время, материал); экспорт G-code; сохранение проекта 3MF

Официальный Python MCP SDK требует Python 3.10+ и внутри слайсера не запустится. Протокол (JSON-RPC 2.0 поверх HTTP/stdio) придётся реализовать самостоятельно в объёме, который нужен для initialize, tools/list и tools/call.

3.5. Схема работы

SPA (HTML/CSS/JS)
   │  HTTP/WebSocket на localhost
Python-плагин: агент (цикл диалога с LLM)
   │                              │
   │ tool calls                   │ OpenAI-совместимый API
MCP-сервер плагина               LLM (URL + ключ организаторов)
   │
API STE Slicer: настройки, профили, сцена, слайсинг

4. Как разработать плагин для STE Slicer (Cura 3.6)

4.1. Где лежат плагины

Встроенные плагины находятся в папке plugins дистрибутива. Они пригодятся как примеры: SupportEraser, PostProcessingPlugin, MachineSettingsAction, 3MFWriter, CuraEngineBackend, CylindricalBackend (5D).

Свой плагин положите в папку plugins внутри папки конфигурации пользователя (в STE Slicer это %APPDATA%\steslicer\7.x\plugins). Открыть папку конфигурации можно через меню Справка → Показать папку конфигурации.

После изменения кода слайсер нужно перезапустить.

4.2. Структура

AIAssistant/
├── plugin.json
├── __init__.py
├── AIAssistant.py      # Extension: пункт меню, локальный сервер, открытие браузера
├── agent/              # цикл общения с LLM, MCP-сервер, инструменты
└── web/                # SPA: index.html, app.js, style.css

plugin.json:

{
    "name": "AI Assistant",
    "author": "Team",
    "version": "1.0.0",
    "description": "LLM chat assistant for STE Slicer",
    "api": 5,
    "i18n-catalog": "steslicer"
}

__init__.py:

from . import AIAssistant

def getMetaData():
    return {}

def register(app):
    return {"extension": AIAssistant.AIAssistant()}

AIAssistant.py (минимальный каркас):

import json
import os
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

from UM.Extension import Extension

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

class ChatServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):              # раздаём web/ вместо текущей папки
        path = super().translate_path(path)
        return os.path.join(WEB_DIR, os.path.relpath(path, os.getcwd()))

    def do_POST(self):                           # JS -> Python
        if self.path != "/api/message":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length).decode("utf-8"))
        body = json.dumps({"reply": "echo: " + data.get("text", "")}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class AIAssistant(Extension):
    def __init__(self):
        super().__init__()
        self.setMenuName("AI Assistant")
        self.addMenuItem("Open chat", self.showChat)
        self._server = None

    def showChat(self):
        if self._server is None:
            self._server = ChatServer(("127.0.0.1", 0), Handler)   # порт выбирает ОС
            threading.Thread(target=self._server.serve_forever, daemon=True).start()
        webbrowser.open("http://127.0.0.1:%d/" % self._server.server_port)

В app.js отправляйте сообщения через fetch("/api/message", {method: "POST", body: JSON.stringify({text})}). Для потоковых событий (ответ модели по частям, прогресс слайсинга) добавьте WebSocket (PyQt5.QtWebSockets.QWebSocketServer) или polling.

Код в этом сервере выполняется не в главном Qt-потоке. Сцену, настройки и слайсинг трогайте только через app.callLater(...), иначе слайсер может упасть.

4.3. Ключевые API (по аналогии с Cura 3.6)

 | Что
 | Как

 | Приложение
 | from steslicer.SteSlicerApplication import SteSlicerApplication; app = SteSlicerApplication.getInstance()

 | Глобальные настройки
 | stack = app.getGlobalContainerStack(); stack.getProperty("layer_height", "value"); stack.userChanges.setProperty("layer_height", "value", 0.2)

 | Настройки экструдера
 | ExtruderManager.getInstance().getActiveExtruderStack() (steslicer/Settings)

 | Профили и материалы
 | app.getMachineManager(): setQualityGroupByQualityType(...), setMaterialById(...), activeQualityType, activeMaterialId

 | Загрузка модели
 | app.readLocalFile(QUrl.fromLocalFile(path))

 | Сцена
 | app.getController().getScene().getRoot(); обход через UM.Scene.Iterator.DepthFirstIterator; изменения через UM.Operations (TranslateOperation, RotateOperation, ScaleOperation)

 | Расстановка
 | app.arrangeAll()

 | Слайсинг
 | app.getBackend() (бэкенды 3D/5D: CuraEngineBackend, CylindricalBackend, см. steslicer/MultiBackend.py); сигналы backendStateChange, processingProgress

 | Результат
 | app.getPrintInformation(): время печати и расход материала

 | Сохранение
 | плагины-писатели 3MFWriter и GCodeWriter (PluginRegistry.getInstance().getPluginObject(...))

Режим печати 3D/5D переключается настройками и профилями машины Stereotech. Ищите соответствующие ключи в определениях принтера в resources/definitions дистрибутива.

Используем ТОЛЬКО режимы 3D (classic), 5D Spiral (cylindrical) и 5D (cylindrical_full)
В качестве основного профиля для тестов используем Stereotech Hybrid 530 V5.2.4

Сцену и настройки можно менять только из главного потока Qt. Если вызов инструмента пришёл из потока сервера или сети, передайте его в главный поток через app.callLater(func, *args).

Логи пишутся в stderr.log и *.log в папке конфигурации. Для отладки используйте from UM.Logger import Logger; Logger.log("d", "...").

5. Что предоставляют организаторы

Доступ к LLM: URL и ключ (OpenAI-совместимый API).

Дистрибутив STE Slicer с инструкцией по активации, на нём проверяется плагин.

Набор 3D-моделей с описанием задачи печати для каждой.

Ссылки на скачивание дистрибутива, инструкцию по активации и форму загрузки результатов будут опубликованы отдельно.

Эталонные 3MF-проекты по каждой модели хранятся у жюри и участникам не выдаются.

6. Проверка

По каждой выданной модели команда через чатбот получает готовый проект и G-code. Жюри сравнивает 3MF-проекты команды с эталонными: режим 3D/5D, профиль и материал, ключевые настройки, ориентацию и расположение модели. Также проверяется, что G-code корректен, и оценивается переписка в чатботе.

7. Что сдать

Один архив через форму организаторов:

<team_name>.zip
├── plugin/              # исходный код плагина + README (установка, настройка URL/ключа)
└── results/
    └── <model_name>/
        ├── project.3mf  # проект, полученный через чатбот
        ├── result.gcode # G-code — результат слайсинга
        └── chat_*.png   # скриншоты переписки в чатботе

8. Критерии оценки

 | №
 | Критерий
 | Что смотрим в этом кейсе

 | 5.4.1
 | Прототип: соответствует ли фактическая функциональность решения заявленной участниками?
 | Плагин ставится в выданный дистрибутив, чат работает, заявленные инструменты действительно меняют настройки и сцену и запускают слайсинг

 | 5.4.2
 | Решение основной проблемы: покрывает ли продукт основную проблему кейса?
 | Насколько близки результаты по тестовым моделям к эталонным 3MF; корректны ли G-code и выбор режима 3D/5D

 | 5.4.3
 | Разработка и внедрение: оправдывает ли эффект от применения затраты на разработку и внедрение?
 | Простота установки и настройки, сопровождаемость кода, скорость получения результата по сравнению с ручной настройкой

 | 5.4.4
 | Новаторские идеи: собственные фичи, напрямую связанные с задачей, или новый подход (не использовался ранее, новая технология, не копия существующих решений)
 | Например: анализ геометрии и фото, рекомендации по ориентации, сравнение вариантов профилей, учёт специфики 5D

 | 5.4.5
 | UI/UX: проработанность пользовательского интерфейса
 | Удобство чата, прикрепления файлов, видимость действий агента, объяснение решений, обработка ошибок

 | 5.4.6
 | Второстепенные проблемы: решает ли продукт второстепенные проблемы из кейса или замеченные участниками?
 | Проблемы 1–4 из раздела 1 и найденные командой

 | 5.4.7
 | Аналитика: насколько полно проведён анализ целевой и потенциальной аудитории, проблем пользовательского опыта, других сервисов и аналогичных продуктов
 | Описание аудитории, обзор аналогов (ИИ-функции в других слайсерах), обоснование решений
