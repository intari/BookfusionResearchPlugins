# BookFusion Back Sync — Calibre Plugin

**Русская версия:** `readme.md` (этот файл)  
**English version:** [README_en.md](README_en.md)

Calibre-плагин для обратной синхронизации: читает даты последнего чтения из BookFusion
и записывает их в выбранную custom-колонку Calibre.

Работает параллельно со штатным плагином BookFusion (они не конфликтуют).

## Об авторе,etc
(c) Dmitriy Kazimirov <dmitriy.kazimirov@viorsan.com>
Также были использованы исходники Calibre Bookfusion Plugin, Calibre Obsidian Plugin, результаты моих старых исследований private API (насколько помню - реверсинг для целей совместимости - по законам России можно)
(когда нужный функционал будет доступен через публичный API - переделаю)

Bookfusion (c) 
## Использование ИИ:
При разработке были использованы:
- Claude Code
- OpenCode с OpenAI Codex

---

## Что делает

1. Авторизуется в BookFusion через email и пароль (Private API).
2. Загружает список всех книг из библиотеки BookFusion.
3. Сопоставляет книги с Calibre по идентификатору `bookfusion` (который штатный плагин
   прописывает в поле Identifiers при загрузке книги): сначала по `BookV3.book_id`,
   затем fallback по `BookV3.id`.
4. Для каждой совпавшей книги записывает дату последнего чтения в выбранную
    custom-колонку типа Date.
5. Перед записью сортирует книги: сначала самые недавно читанные, книги без даты — в конце.

Источник даты — в порядке приоритета:
- `last_read_at` из BookFusion API (если не пустое)
- `reading_position.updated_at` — дата последнего обновления позиции чтения (используется
  чаще всего, потому что `last_read_at` заполняется только в мобильном приложении)

Лог в диалоге показывает для каждой книги: какая дата записана, из какого поля взята,
и как именно книга была сопоставлена (`match=book_id` или `match=id`).

---

## Требования

- Calibre 6.2.1 или новее
- Штатный плагин BookFusion уже установлен и хотя бы один раз синхронизирован
  (чтобы в книгах был прописан идентификатор `bookfusion`)
- Аккаунт BookFusion с email и паролем (не OAuth через Facebook/Twitter)
- Кастомная колонка типа Date в Calibre (например `#dateread`)

---

## Установка

1. Скачать `BookfusionBackSync.zip` из корня репозитория.

2. В Calibre: **Preferences → Plugins → Load plugin from file** → выбрать ZIP.

3. Перезапустить Calibre.

4. Кнопка **BookFusion Back Sync** появится на панели инструментов.

---

## Настройка

Открыть настройки: кнопка **Settings** в диалоге плагина, или
**Preferences → Plugins → BookFusion Back Sync → Customize**.

| Поле | Описание |
|------|----------|
| BookFusion Email | Email аккаунта BookFusion |
| Password | Пароль аккаунта |
| Last Read Column | Custom-колонка Calibre типа Date, куда писать дату |

Пароль хранится в открытом виде в файле конфигурации Calibre
(`plugins/bookfusionbacksync.json`) — аналогично тому, как штатный плагин
хранит API-ключ.

Device ID генерируется автоматически при первом синке и сохраняется навсегда.

---

## Использование

**Выделять книги не нужно** — плагин синхронизирует всю библиотеку целиком.

1. Нажать кнопку **BookFusion Back Sync** на панели инструментов.
2. Нажать **Sync Now**.
3. Наблюдать прогресс в лог-окне.
4. После завершения Calibre автоматически обновит список книг.

### Что видно во время синка

Строка статуса над прогресс-баром последовательно показывает:

| Статус | Что происходит |
|--------|----------------|
| `Authenticating…` | Вход через email/пароль, получение токена |
| `Fetching BookFusion library…` | Загрузка всех книг из BookFusion (постранично) |
| `Scanning Calibre library…` | Поиск книг с идентификатором `bookfusion` — здесь заполняется прогресс-бар |
| `Writing N dates to Calibre…` | Запись найденных дат одним вызовом |
| `Done — N updated, M skipped.` | Готово |

Прогресс-бар заполняется на этапе сопоставления книг Calibre с BookFusion.
Первые два шага (auth + загрузка из сети) идут без процентов.

### Лог

Для каждой обновлённой книги строка вида:
```
OK    The Name of the Wind  →  2024-11-03  (from reading_position.updated_at)
OK    Dune                  →  2025-01-15  (from last_read_at, match=book_id)
```

Книги без совпадения в BookFusion — молча пропускаются (учитываются в `M skipped`).

Книга пропускается с записью `SKIP` только если дата есть в BookFusion, но не парсится.

### Отмена

Нажать **Close** во время синка — worker остановится корректно (ждёт до 3 секунд).

---

## Как устроен

### API

Плагин использует Private API BookFusion (`https://bookfusion.com/api`) — тот же,
что использует мобильное приложение. Официальной документации нет; API восстановлен
методом реверс-инжиниринга из исходников Android-клиента (2014) и fusionfixer (2018).

Авторизация: `POST /v1/auth.json` с полями `device`, `login`, `password` → возвращает `token`.
Токен используется как query-параметр (`?device=...&token=...`) во всех последующих GET-запросах.

Библиотека: `GET /v3/library/books.json?page=N&per_page=100` — постраничная выгрузка.
Каждая книга (`BookV3`) содержит:
- `book_id` — глобальный ID книги (обычно именно он хранится в `identifiers['bookfusion']`)
- `id` — ID записи книги в библиотеке пользователя
- `last_read_at` — дата последнего чтения (часто `null`)
- `reading_position.updated_at` — дата последнего обновления позиции чтения

HTTP-запросы делаются через стандартную библиотеку Python (`urllib.request`) —
без внешних зависимостей.

### Сопоставление книг

Штатный BookFusion плагин при загрузке книги сохраняет её ID в поле Calibre:
```
Identifiers → bookfusion: 66816
```

Плагин Back Sync читает это значение и сравнивает с `BookV3.book_id` из API
(а также с fallback на `BookV3.id` для совместимости старых записей).
Совпадение — запись даты в выбранную колонку.

### Запись в Calibre

Все обновления записываются одним вызовом Calibre new_api:
```python
db.set_field('#dateread', {calibre_book_id: datetime_object, ...})
```

### Структура файлов

| Файл | Назначение |
|------|-----------|
| `__init__.py` | Регистрация плагина, метаданные, точка входа |
| `plugin-import-name-bookfusionbacksync.txt` | Import-name для Calibre plugin loader |
| `config.py` | JSONConfig с настройками; ConfigWidget (форма настроек) |
| `ui.py` | InterfacePlugin — пункт меню и кнопка в Calibre |
| `main.py` | MainDialog — диалог с прогресс-баром и логом |
| `sync_worker.py` | SyncWorker (QThread) — вся логика синка |
