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

BookFusion не отдаёт данные о прогрессе чтения ни через Calibre API, ни через Obsidian API. Плагин построить невозможно — данных нет.
