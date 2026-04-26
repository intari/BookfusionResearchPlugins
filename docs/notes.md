# Notes

## Плагин для синхронизации last read date в Calibre

**Вопрос:** можно ли сделать Calibre-плагин, который обновляет дату последнего чтения для синхронизированных книг?

**Вывод: API недостаточно.**

`POST /obsidian-api/sync` — единственный endpoint, возвращающий данные обратно. Ответ:

```json
{
  "pages": [...],
  "cursor": "...",
  "next_sync_cursor": "..."
}
```

`BookPage` содержит поля: `id`, `frontmatter`, `content`, `highlights`, `atomic_highlights`, `directory`, `filename`, `update_strategy` — структура заметок Obsidian, ничего про прогресс чтения.

Calibre API (`PUT /uploads/{id}`, `POST /uploads/finalize`) принимает metadata: title, authors, bookshelves, cover, isbn, issued_on, language, series, summary, tags. Поля `last_read_date` и `reading_progress` отсутствуют.

BookFusion не отдаёт данные о прогрессе чтения ни через Calibre API, ни через Obsidian API. Через эти API плагин построить невозможно.

**Обновление:** через Private API (`GET /v3/library/books.json`) данные есть. Плагин реализован — см. `BookfusionBackSync/`.

---

## BookfusionBackSync — плагин обратной синхронизации

**Расположение:** `BookfusionBackSync/`

**Как работает:**
1. Авторизация через Private API: `POST /api/v1/auth.json` (email + password)
2. Загрузка всех книг: `GET /api/v3/library/books.json` (постраничная, 100 за раз)
3. Сопоставление по идентификатору: `identifiers['bookfusion']` в Calibre = `BookV3.id` из Private API
4. Запись даты в выбранную custom column Calibre одним вызовом `db.set_field()`

**Источник даты:** `BookV3.last_read_at` (если не null), иначе `BookV3.reading_position.updated_at`. В тестовых данных `last_read_at` всегда null, `reading_position.updated_at` имеет реальные значения.

**Настройки (через Calibre Preferences → Plugins):**
- Email и пароль от аккаунта BookFusion
- Целевое поле Calibre (dropdown по datetime-колонкам, по умолчанию `#dateread`)
- Device ID генерируется один раз при первом синке и сохраняется навсегда

**Важно:** плагин читает только Books из Private API. Запись обратно в BookFusion не производится.
