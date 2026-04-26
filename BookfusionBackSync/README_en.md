# BookFusion Back Sync - Calibre Plugin

**English version:** `README_en.md` (this file)  
**Russian version:** [readme.md](readme.md)

Calibre plugin for reverse sync: reads last-read dates from BookFusion
and writes them into a selected Calibre custom date column.

It works alongside the official BookFusion Calibre plugin (no conflicts).

Login/password credentials are used **only** for BookFusion API authentication
and are never sent to the plugin developer.

## About the author, etc
(c) Dmitriy Kazimirov <dmitriy.kazimirov@viorsan.com>
This project also uses ideas and findings from the Calibre BookFusion plugin,
the Calibre Obsidian plugin, and my earlier private API research
(as far as I remember, done for compatibility purposes).



## AI usage
Used during development:
- Claude Code
- OpenCode with OpenAI Codex

---

## What it does

1. Authenticates to BookFusion using email and password (Private API).
2. Fetches the full list of books from the BookFusion library.
3. Matches books to Calibre by the `bookfusion` identifier (written by the
   official plugin into Calibre Identifiers when a book is uploaded): first by
   `BookV3.book_id`, then with fallback to `BookV3.id`.
4. Writes the last-read date for each matched book into the selected
   Calibre custom Date column.
5. Sorts processing order so the most recently read books are written first;
   books without dates are processed last.
6. Optionally sets a Completed flag in a selected Calibre Yes/No column when
   `reading_position.percentage` is above the configured threshold.

Date source priority:
- `last_read_at` from BookFusion API (when present)
- `reading_position.updated_at` (used most often, because `last_read_at`
  is usually populated only by the mobile app)

The dialog log shows, for each book, which date was written, from which field,
and which id mapping was used (`match=book_id` or `match=id`).

---

## Requirements

- Calibre 6.2.1 or newer
- Official BookFusion plugin installed and synced at least once
  (so books already have the `bookfusion` identifier)
- BookFusion account with email/password (not Facebook/Twitter OAuth)
- A custom Date column in Calibre (for example `#dateread`)

---

## Installation

1. Download `BookfusionBackSync.zip` from the repository root.

2. In Calibre: **Preferences -> Plugins -> Load plugin from file** and select the ZIP.

3. Restart Calibre.

4. The **BookFusion Back Sync** button appears in the toolbar.

---

## Configuration

Open settings using the **Settings** button in the plugin dialog, or:
**Preferences -> Plugins -> BookFusion Back Sync -> Customize**.

| Field | Description |
|------|-------------|
| BookFusion Email | BookFusion account email |
| Password | Account password |
| Last Read Column | Calibre custom Date column to write into |
| Completed Column (bool) | Optional Calibre Yes/No column for completed books |
| Completed Threshold (%) | Completion threshold in percent (default `98.9`) |
| Fetch Page Size | Page size for `/v3/library/books.json` fetch (default `1337`) |
| Fetch Timeout (sec) | Library fetch request timeout in seconds (default `90`) |
| Full SKIP Logs | Log all `SKIP` lines (otherwise only a limited sample is written) |
| Batch UI Logs | Batch log updates in UI; batch size is dynamic and never exceeds `0.5%` of total books |

Password is stored as plain text in Calibre config
(`plugins/bookfusionbacksync.json`), similar to how the official plugin stores the API key.

In other words: credentials are stored locally on your machine and used only
for BookFusion requests.

Device ID is generated automatically on the first sync and then persisted.

---

## Usage

You do **not** need to select books. The plugin syncs the whole library.

1. Click **BookFusion Back Sync** in the toolbar.
2. Click **Sync Now**.
3. Watch progress in the log area.
4. After completion, Calibre refreshes the book list automatically.

### What you see during sync

The status line above the progress bar shows these stages:

| Status | Meaning |
|--------|---------|
| `Authenticating...` | Login with email/password, token retrieval |
| `Fetching BookFusion library...` | Downloading all books from BookFusion (paged) |
| `Scanning Calibre library...` | Matching books with `bookfusion` identifiers - progress bar fills here |
| `Writing N dates to Calibre...` | Writing all found dates in one call |
| `Done - N updated, M skipped.` | Finished |

The dialog has two progress bars:
- top bar: BookFusion library fetch,
- bottom bar: Calibre matching and writes.

Both progress bars update only when integer percent changes.

### Log

For each updated book, lines look like:
```text
OK    The Name of the Wind  ->  2024-11-03  (from reading_position.updated_at)
OK    Dune                  ->  2025-01-15  (from last_read_at, match=book_id)
OK    Dune                  ->  Completed=True  (percentage=100.000, threshold=99.90, match=book_id)
```

Books without a match in BookFusion are skipped silently (counted in `M skipped`).

A book gets a visible `SKIP` line only when a date exists in BookFusion but cannot be parsed.

When `Full SKIP Logs` is disabled, only a limited sample of `SKIP` lines is written to file logs,
while full skip counts remain available in the final `Match stats` line.

### Cancel

Click **Close** during sync - worker stops gracefully (waits up to 3 seconds).

---

## How it works

### API

The plugin uses BookFusion Private API (`https://bookfusion.com/api`) - the same API
used by the mobile app. There is no official public documentation; the API was
reconstructed from Android client (2014) and fusionfixer (2018) source analysis.

Auth: `POST /v1/auth.json` with `device`, `login`, `password` returns `token`.
The token is then used as query params (`?device=...&token=...`) in GET requests.

Library: `GET /v3/library/books.json?page=N&per_page=100` for paginated export.
Each `BookV3` item includes:
- `book_id` - global book id (this is usually what `identifiers['bookfusion']` stores)
- `id` - user-library record id
- `last_read_at` - last read timestamp (often `null`)
- `reading_position.updated_at` - last reading position update timestamp
- `reading_position.percentage` - read percentage (used for Completed flag)

HTTP calls are made with Python standard library (`urllib.request`),
without external dependencies.

### Book matching

The official BookFusion plugin stores the remote id in Calibre:
```text
Identifiers -> bookfusion: 66816
```

Back Sync reads this value and compares it with `BookV3.book_id` from API
(with fallback to `BookV3.id` for compatibility with older records).
If matched, it writes the date to the selected column.

### Writing into Calibre

All updates are written in one Calibre `new_api` call:
```python
db.set_field('#dateread', {calibre_book_id: datetime_object, ...})
```

### File structure

| File | Purpose |
|------|---------|
| `__init__.py` | Plugin registration, metadata, entry point |
| `plugin-import-name-bookfusionbacksync.txt` | Import name for Calibre plugin loader |
| `config.py` | JSONConfig settings and ConfigWidget form |
| `ui.py` | InterfacePlugin - menu action and toolbar button |
| `main.py` | MainDialog - dialog with progress bar and log |
| `sync_worker.py` | SyncWorker (QThread) - sync logic |
