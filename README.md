# BookFusion Plugins Research

Реверс-инжиниринг semi-public REST API сервиса [BookFusion](https://www.bookfusion.com)
по исходникам двух официальных плагинов. Результат — документация API, тесты и
Calibre-плагин для обратной синхронизации дат чтения.

Исходный url - https://git.viorsan.com/vrr/BookfusionPluginsResearch
Зеркало https://github.com/intari/BookfusionResearchPlugins
---

## Структура репозитория

| Путь | Описание |
|------|----------|
| `calibre-plugin/` | Исходники официального Calibre-плагина BookFusion (только чтение) |
| `obsidian-plugin/` | Исходники официального Obsidian-плагина BookFusion (только чтение) |
| `docs/api.md` | Документация API, восстановленная из исходников |
| `docs/tasks/api-research.md` | Тикет с полным результатом исследования |
| `docs/notes.md` | Заметки по архитектуре Back Sync и Private API |
| `tests/` | Тесты Calibre API и Obsidian API (pytest + bash/curl) |
| `private_api/` | Документация и тесты Private API BookFusion |
| `BookfusionBackSync/` | Исходники Calibre-плагина Back Sync |
| `BookfusionBackSync.zip` | Готовый архив плагина для установки в Calibre |

---

## BookFusion API

Два semi-public REST API без официальной документации:

| API | Base URL | Аутентификация |
|-----|----------|----------------|
| Calibre API v1 | `https://www.bookfusion.com/calibre-api/v1` | HTTP Basic: `base64(api_key:)` |
| Obsidian API | `https://www.bookfusion.com` | Заголовок `X-Token: {token}` |

Полная документация со всеми эндпоинтами, структурами запросов и ответов —
в [`docs/api.md`](docs/api.md).

---

## Тесты

Тесты охватывают оба API. Obsidian happy-path тесты требуют `OBSIDIAN_TOKEN`
(получается однократно через браузер — см. `docs/api.md`, раздел 2.2).

```bash
pip install pytest requests

# pytest
export API_USER=your_bookfusion_api_key
pytest tests/ -v

# bash/curl (WSL / Linux)
export API_USER=your_bookfusion_api_key
bash tests/test_api.sh
```

---

## BookFusion Back Sync

Calibre-плагин, который читает даты последнего чтения из BookFusion и записывает
их в выбранную custom-колонку Calibre (тип Date).

**Установка:** скачать `BookfusionBackSync.zip` →
Calibre **Preferences → Plugins → Load plugin from file**.

Подробнее — в [`BookfusionBackSync/readme.md`](BookfusionBackSync/readme.md).
