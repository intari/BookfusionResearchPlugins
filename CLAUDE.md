# BookFusion API — реверс-инжиниринг

## Контекст проекта

Задача#1: восстановить документацию по semi-public REST API сервиса BookFusion
и написать тесты которые проверяют что API работает.
Задача#2: сделать BookfusionBackSync плагин для синхронизации "назад"

Официальной документации нет. Источники знаний — исходники plugin'ов
- Obsidian Plugin https://github.com/BookFusion/obsidian-plugin
- Calibre Plugin https://github.com/BookFusion/calibre-plugin


## Структура репозитория

```
calibre-plugin/      # Bookfusion Plugin для Calibre использующий Bookfusion Semipublic API 
obsidian-plugin/      # Obsidian Plugin для Calibre использующий Bookfusion Semipublic API 

docs/
  api.md             # документация по API (генерируем)
  tasks/             # тикеты на работы

tests/
  test_api.py        # pytest тесты (генерируем)
  test_api.sh        # bash/curl тесты (генерируем)
```

## Правила работы

- **Не выдумывать** эндпоинты и поля — только то что есть в исходниках
- Неуверенные места помечать комментарием `# UNVERIFIED`
- Если поле есть в request-entity но неясно обязательное ли оно — помечать `# optional?`
- Все находки фиксировать в тикете перед реализацией
- В документации ЗАПРЕЩЕНО писать "и др.", "и другие", "и т.д.", 
  "богатая структура", "включает множество полей" и подобное
- Каждая структура описывается полностью — все поля, все типы, 
  все возможные значения enum
- Если структура большая — это не повод сокращать, 
  это повод сделать подробную таблицу


## Этапы (выполнять последовательно)

### Этап 1 — Исследование
Создать `docs/tasks/api-research.md`:
- Полный список эндпоинтов 
- Структуры всех request/response entity

### Этап 2 — Документация
Создать `docs/api.md`:
- Секция Auth отдельно и первой
- Для каждого эндпоинта: метод, путь, параметры, тело запроса, тело ответа, пример


### Этап 3 — Тесты Python
Создать `tests/auth.py` и `tests/test_api.py`:
- `auth.py` — функция `get_token()` и pytest fixture `scope="session"`
- Переменные окружения: `API_BASE_URL`, `API_USER`, `API_PASS`, `API_DEVICE`
- Каждый тест независим
- Сначала happy path, потом edge cases
- Запускаться в WSL: `pytest tests/ -v`

### Этап 4 — Тесты bash
Создать `tests/test_api.sh`:
- Использует curl
- Те же переменные окружения
- Цветной вывод: PASS/FAIL
- Запускаться в WSL: `bash tests/test_api.sh`

## Среда запуска тестов

- WSL (Ubuntu)
- Python 3.x, pytest, requests
- bash, curl, jq

## Чего НЕ делать

- Не трогать исходники  — только читать
- Не писать тесты которые меняют данные без явного указания (DELETE, POST осторожно)
- Не хардкодить credentials в тестах — только через env переменные