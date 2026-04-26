# BookFusion API

> Документация восстановлена из исходников `calibre-plugin/` и `obsidian-plugin/`.  
> `# UNVERIFIED` — поле или поведение не верифицированы живым трафиком.

---

## Оглавление

1. [Обзор](#1-обзор)
2. [Аутентификация](#2-аутентификация)
   - [2.1 Calibre API — HTTP Basic Auth](#21-calibre-api--http-basic-auth)
   - [2.2 Obsidian API — Token](#22-obsidian-api--token)
3. [Calibre API](#3-calibre-api)
   - [GET /calibre-api/v1/limits](#get-calibre-apiv1limits)
   - [GET /calibre-api/v1/uploads/{id}](#get-calibre-apiv1uploadsid)
   - [GET /calibre-api/v1/uploads](#get-calibre-apiv1uploads)
   - [POST /calibre-api/v1/uploads/init](#post-calibre-apiv1uploadsinit)
   - [POST {upload_url}](#post-upload_url--внешнее-хранилище)
   - [POST /calibre-api/v1/uploads/finalize](#post-calibre-apiv1uploadsfinalize)
   - [PUT /calibre-api/v1/uploads/{id}](#put-calibre-apiv1uploadsid)
4. [Obsidian API](#4-obsidian-api)
   - [GET /obsidian-api/connect](#get-obsidian-apiconnect)
   - [POST /obsidian-api/sync](#post-obsidian-apisync)
5. [Структуры данных](#5-структуры-данных)
   - [5.1 Page](#51-page)
   - [5.2 BookPage](#52-bookpage)
   - [5.3 IndexPage](#53-indexpage)
   - [5.4 HighlightBlock](#54-highlightblock)
   - [5.5 AtomicHighlightPage](#55-atomichighlightpage)
6. [Алгоритм calibre_metadata_digest](#6-алгоритм-calibre_metadata_digest)
7. [Magic-комментарии Obsidian](#7-magic-комментарии-obsidian)
8. [Поддерживаемые форматы файлов](#8-поддерживаемые-форматы-файлов)

---

## 1. Обзор

BookFusion предоставляет два независимых REST API с разными механизмами аутентификации:

| API | Базовый URL | Назначение |
|-----|-------------|------------|
| Calibre API v1 | `https://www.bookfusion.com/calibre-api/v1` | Загрузка книг из Calibre |
| Obsidian API | `https://www.bookfusion.com` | Синхронизация заметок и хайлайтов с Obsidian |

---

## 2. Аутентификация

### 2.1 Calibre API — HTTP Basic Auth

Каждый запрос к Calibre API требует двух заголовков:

| Заголовок | Значение |
|-----------|----------|
| `Authorization` | `Basic {base64("{api_key}:")}` |
| `User-Agent` | `BookFusion Calibre Plugin {major}.{minor}.{patch}` |

**`{api_key}`** — API-ключ пользователя; используется как HTTP username, пароль — пустая строка.

Пример для ключа `abc123` (плагин версии 1.4.0):

```
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
```

> `base64("abc123:")` = `YWJjMTIzOg==`

API-ключ пользователь получает на странице (HTML, не API-эндпоинт):  
`https://www.bookfusion.com/calibre-api/v1/api-key`

При неверном ключе сервер возвращает HTTP `401`.

---

### 2.2 Obsidian API — Token

Каждый запрос к Obsidian API (кроме `GET /obsidian-api/connect`) требует заголовка:

```
X-Token: {token}
```

**Получение токена** — однократная операция через браузер:

1. Открыть в браузере:  
   `GET https://www.bookfusion.com/obsidian-api/connect?_={unix_timestamp_ms}`
2. Пользователь входит в аккаунт BookFusion.
3. BookFusion вызывает Obsidian protocol handler:  
   `obsidian://bookfusion-connect?token={token}`
4. Obsidian-плагин сохраняет `token` и использует его в последующих запросах.

---

## 3. Calibre API

**Базовый URL:** `https://www.bookfusion.com/calibre-api/v1`

Все запросы к Calibre API требуют заголовков `Authorization` и `User-Agent` из раздела 2.1.

---

### GET /calibre-api/v1/limits

Возвращает лимиты аккаунта. Вызывается перед началом синхронизации.

#### Запрос

```http
GET /calibre-api/v1/limits HTTP/1.1
Host: www.bookfusion.com
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
```

Query-параметры отсутствуют.

#### Ответ `200 OK`

```json
{
  "filesize": 52428800,
  "total_books": 100,
  "message": "You've reached the book limit for your plan. Upgrade to sync more books."
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `filesize` | `integer` | Максимальный размер файла книги в байтах |
| `total_books` | `integer \| null` | Максимальное количество книг. `null` — без ограничений |
| `message` | `string \| null` | Сообщение для отображения пользователю при превышении лимита. `null` — нет сообщения |

#### Ошибки

| Код | Описание |
|-----|----------|
| 401 | Неверный API-ключ |

---

### GET /calibre-api/v1/uploads/{id}

Проверяет, загружена ли книга в BookFusion. Возвращает объект с ID и дайджестом метаданных, если книга найдена.

Используется в двух сценариях:

| Сценарий | Значение `{id}` |
|----------|-----------------|
| У книги в Calibre есть идентификатор `bookfusion` | BookFusion ID (целое число) |
| У книги нет ни `bookfusion`, ни `isbn` | SHA-256 hex-дайджест содержимого файла |

#### Path-параметры

| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | `string` | BookFusion ID книги (число) или SHA-256 hex-дайджест файла |

#### Запрос (по BookFusion ID)

```http
GET /calibre-api/v1/uploads/42 HTTP/1.1
Host: www.bookfusion.com
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
```

#### Запрос (по SHA-256 дайджесту)

```http
GET /calibre-api/v1/uploads/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 HTTP/1.1
Host: www.bookfusion.com
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
```

#### Ответ `200 OK`

Единственный объект (не массив).

```json
{
  "id": 42,
  "calibre_metadata_digest": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `integer` | BookFusion внутренний ID книги # UNVERIFIED |
| `calibre_metadata_digest` | `string` | SHA-256 hex-дайджест метаданных предыдущей загрузки (алгоритм — раздел 6) |

#### Ошибки

| Код | Описание |
|-----|----------|
| 401 | Неверный API-ключ |
| 404 | Книга не найдена |
| 500 | Внутренняя ошибка сервера |

---

### GET /calibre-api/v1/uploads

Ищет загруженную книгу по ISBN. Используется если у книги в Calibre есть идентификатор `isbn`, но нет `bookfusion`.

#### Query-параметры

| Параметр | Тип | Обязательный | Описание |
|----------|-----|:---:|----------|
| `isbn` | `string` | да | ISBN книги |

#### Запрос

```http
GET /calibre-api/v1/uploads?isbn=9780743273565 HTTP/1.1
Host: www.bookfusion.com
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
```

#### Ответ `200 OK`

Массив объектов. При отсутствии совпадений — пустой массив `[]`.  
Клиент использует только первый элемент массива.

```json
[
  {
    "id": 42,
    "calibre_metadata_digest": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
  }
]
```

Поля элемента:

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `integer` | BookFusion внутренний ID книги # UNVERIFIED |
| `calibre_metadata_digest` | `string` | SHA-256 hex-дайджест метаданных предыдущей загрузки |

#### Ошибки

| Код | Описание |
|-----|----------|
| 401 | Неверный API-ключ |
| 500 | Внутренняя ошибка сервера |

---

### POST /calibre-api/v1/uploads/init

Инициализирует загрузку новой книги. Возвращает presigned URL и параметры для загрузки файла напрямую во внешнее хранилище (S3 или аналогичное).

Вызывается только для книг, не найденных через `GET /uploads/{id}` или `GET /uploads?isbn=`.

#### Запрос

Content-Type: `multipart/form-data`

```http
POST /calibre-api/v1/uploads/init HTTP/1.1
Host: www.bookfusion.com
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
Content-Type: multipart/form-data; boundary=----Boundary

------Boundary
Content-Disposition: form-data; name="filename"

the-great-gatsby.epub
------Boundary
Content-Disposition: form-data; name="digest"

e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
------Boundary--
```

| Поле | Тип | Обязательный | Описание |
|------|-----|:---:|----------|
| `filename` | `string` | да | Имя файла книги (basename), например `book.epub` |
| `digest` | `string` | да | SHA-256 hex-дайджест содержимого файла |

#### Ответ `200 OK`

```json
{
  "url": "https://<storage-host>/<bucket>",
  "params": {
    "key": "uploads/abc123def456/the-great-gatsby.epub",
    "<param2>": "<value2>",
    "<param3>": "<value3>"
  }
}
```

> Конкретные ключи `params` зависят от провайдера хранилища и не зафиксированы в исходниках плагина. Гарантированно присутствует только ключ `key`. # UNVERIFIED

| Поле | Тип | Описание |
|------|-----|----------|
| `url` | `string` | URL внешнего хранилища для загрузки файла |
| `params` | `object<string, string>` | Поля для multipart-запроса к `url`. Конкретные ключи зависят от провайдера хранилища. Гарантированно содержит ключ `key` (используется при финализации). Остальные ключи не зафиксированы. # UNVERIFIED |

#### Ошибки

| Код | Тело ответа | Описание |
|-----|-------------|----------|
| 401 | — | Неверный API-ключ |
| 422 | `{"error": "..."}` | Ошибка валидации |

---

### POST {upload_url} — внешнее хранилище

Загружает файл книги во внешнее хранилище. URL и параметры получены из ответа `POST /uploads/init`.

**Это не BookFusion API** — запрос отправляется на `url` из ответа предыдущего шага (S3 или аналогичный сервис). Заголовки аутентификации BookFusion не передаются.

#### Запрос

Content-Type: `multipart/form-data`

Сначала все поля из объекта `params` ответа `/uploads/init`, последним — поле `file`:

```http
POST https://<storage-host>/<bucket> HTTP/1.1
Content-Type: multipart/form-data; boundary=----Boundary

------Boundary
Content-Disposition: form-data; name="key"

uploads/abc123def456/the-great-gatsby.epub
------Boundary
Content-Disposition: form-data; name="<param2>"

<value2>
------Boundary
Content-Disposition: form-data; name="<param3>"

<value3>
------Boundary
Content-Disposition: form-data; name="file"; filename="the-great-gatsby.epub"

(binary file content)
------Boundary--
```

> Конкретные имена и значения полей (`<param2>`, `<param3>`, ...) определяются объектом `params` из ответа `POST /uploads/init`. В исходниках плагина они не зафиксированы — передаются итерацией по всем ключам `params`. Гарантированно присутствует только `key`. # UNVERIFIED

| Поле | Тип | Описание |
|------|-----|----------|
| *(все ключи из `params`)* | `string` | Поля из объекта `params` ответа `/uploads/init` |
| `file` | `binary` | Содержимое файла книги. Передаётся последним полем. |

#### Ответ

Тело ответа не используется. Успех — HTTP 2xx.

При сетевых ошибках (connection refused, remote host closed, host not found, timeout, temporary network failure) клиент выполняет до двух повторных попыток.

---

### POST /calibre-api/v1/uploads/finalize

Завершает загрузку: регистрирует книгу в BookFusion и привязывает загруженный файл к метаданным.

Вызывается после успешной загрузки файла во внешнее хранилище.

#### Запрос

Content-Type: `multipart/form-data`

```http
POST /calibre-api/v1/uploads/finalize HTTP/1.1
Host: www.bookfusion.com
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
Content-Type: multipart/form-data; boundary=----Boundary

------Boundary
Content-Disposition: form-data; name="key"

uploads/abc123def456/the-great-gatsby.epub
------Boundary
Content-Disposition: form-data; name="digest"

e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
------Boundary
Content-Disposition: form-data; name="metadata[calibre_metadata_digest]"

9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
------Boundary
Content-Disposition: form-data; name="metadata[title]"

The Great Gatsby
------Boundary
Content-Disposition: form-data; name="metadata[summary]"

A story of the fabulously wealthy Jay Gatsby and his love for Daisy Buchanan.
------Boundary
Content-Disposition: form-data; name="metadata[language]"

eng
------Boundary
Content-Disposition: form-data; name="metadata[isbn]"

9780743273565
------Boundary
Content-Disposition: form-data; name="metadata[issued_on]"

1925-04-10
------Boundary
Content-Disposition: form-data; name="metadata[series][][title]"

The Jazz Age Collection
------Boundary
Content-Disposition: form-data; name="metadata[series][][index]"

1.0
------Boundary
Content-Disposition: form-data; name="metadata[author_list][]"

F. Scott Fitzgerald
------Boundary
Content-Disposition: form-data; name="metadata[tag_list][]"

fiction
------Boundary
Content-Disposition: form-data; name="metadata[tag_list][]"

classic
------Boundary
Content-Disposition: form-data; name="metadata[bookshelves][]"


------Boundary
Content-Disposition: form-data; name="metadata[bookshelves][]"

American Literature
------Boundary
Content-Disposition: form-data; name="metadata[cover]"; filename="cover.jpg"

(binary image data)
------Boundary--
```

| Поле | Тип | Обязательный | Описание |
|------|-----|:---:|----------|
| `key` | `string` | да | Значение `params.key` из ответа `/uploads/init` |
| `digest` | `string` | да | SHA-256 hex-дайджест содержимого файла книги |
| `metadata[calibre_metadata_digest]` | `string` | да | SHA-256 hex-дайджест метаданных (алгоритм — раздел 6) |
| `metadata[title]` | `string` | да | Название книги |
| `metadata[summary]` | `string` | нет | Аннотация |
| `metadata[language]` | `string` | нет | Язык книги (первый элемент из списка языков Calibre) |
| `metadata[isbn]` | `string` | нет | ISBN |
| `metadata[issued_on]` | `string` | нет | Дата публикации, формат `YYYY-MM-DD`. Не передаётся если значение равно `0101-01-01` |
| `metadata[series][][title]` | `string` | нет | Название серии. Повторяется для каждой серии отдельной строкой. |
| `metadata[series][][index]` | `string` | нет | Порядковый номер в серии. Передаётся вместе с `series[][title]`; отсутствует если index равен `None`. |
| `metadata[author_list][]` | `string` | нет | Автор. Повторяется для каждого автора. |
| `metadata[tag_list][]` | `string` | нет | Тег. Повторяется для каждого тега. |
| `metadata[bookshelves][]` | `string` | нет | Полка. Первый элемент — обязательно пустая строка (Rails-паттерн для гарантированной передачи массива); затем — названия полок. Поле передаётся только если в настройках Calibre-плагина задана `bookshelves_custom_column`. |
| `metadata[cover]` | `binary` | нет | Файл обложки книги |

#### Ответ `200 OK`

```json
{
  "id": 42
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `integer` | BookFusion внутренний ID созданной книги |

#### Ошибки

| Код | Тело ответа | Описание |
|-----|-------------|----------|
| 401 | — | Неверный API-ключ |
| 422 | `{"error": "..."}` | Ошибка валидации |

---

### PUT /calibre-api/v1/uploads/{id}

Обновляет метаданные существующей книги. Опционально — перезагружает файл книги.

#### Path-параметры

| Параметр | Тип | Описание |
|----------|-----|----------|
| `id` | `string` | BookFusion ID книги |

#### Запрос

Content-Type: `multipart/form-data`

Минимальный пример (обновление метаданных без перезагрузки файла):

```http
PUT /calibre-api/v1/uploads/42 HTTP/1.1
Host: www.bookfusion.com
Authorization: Basic YWJjMTIzOg==
User-Agent: BookFusion Calibre Plugin 1.4.0
Content-Type: multipart/form-data; boundary=----Boundary

------Boundary
Content-Disposition: form-data; name="metadata[calibre_metadata_digest]"

a4e624d686e03ed2767c0abd85c46f3d32c3f784a9d4c851d30de5dd9a26bade
------Boundary
Content-Disposition: form-data; name="metadata[title]"

The Great Gatsby (Updated Edition)
------Boundary
Content-Disposition: form-data; name="metadata[author_list][]"

F. Scott Fitzgerald
------Boundary--
```

| Поле | Тип | Обязательный | Описание |
|------|-----|:---:|----------|
| `file` | `binary` | нет | Файл книги. Передаётся только при явной перезагрузке. |
| `metadata[calibre_metadata_digest]` | `string` | да | SHA-256 hex-дайджест метаданных |
| `metadata[title]` | `string` | да | Название книги |
| `metadata[summary]` | `string` | нет | Аннотация |
| `metadata[language]` | `string` | нет | Язык |
| `metadata[isbn]` | `string` | нет | ISBN |
| `metadata[issued_on]` | `string` | нет | Дата публикации `YYYY-MM-DD` |
| `metadata[series][][title]` | `string` | нет | Название серии (повторяется) |
| `metadata[series][][index]` | `string` | нет | Номер в серии (повторяется; отсутствует если index равен `None`) |
| `metadata[author_list][]` | `string` | нет | Автор (повторяется) |
| `metadata[tag_list][]` | `string` | нет | Тег (повторяется) |
| `metadata[bookshelves][]` | `string` | нет | Полка (первый элемент — пустая строка, затем значения) |
| `metadata[cover]` | `binary` | нет | Файл обложки книги |

#### Ответ `200 OK`

Тело ответа не определено. # UNVERIFIED

#### Ошибки

| Код | Тело ответа | Описание |
|-----|-------------|----------|
| 401 | — | Неверный API-ключ |
| 422 | `{"error": "..."}` | Ошибка валидации |

---

## 4. Obsidian API

**Базовый URL:** `https://www.bookfusion.com`

Все запросы к Obsidian API (кроме `GET /obsidian-api/connect`) требуют заголовка `X-Token` из раздела 2.2.

---

### GET /obsidian-api/connect

Страница аутентификации в браузере. Используется для получения токена.

**Возвращает HTML-страницу, не JSON.**

#### Query-параметры

В каждом запросе передаётся ровно один из двух параметров:

| Параметр | Тип | Сценарий | Описание |
|----------|-----|----------|----------|
| `_` | `string` | Новое подключение | Unix timestamp в миллисекундах. Служит cache buster. |
| `token` | `string` | Повторное открытие страницы настроек | Существующий токен пользователя. |

#### Запрос — новое подключение

```http
GET /obsidian-api/connect?_=1745658000000 HTTP/1.1
Host: www.bookfusion.com
```

#### Запрос — открытие страницы настроек

```http
GET /obsidian-api/connect?token=tok_abc123def456 HTTP/1.1
Host: www.bookfusion.com
```

#### Ответ

HTML-страница. После успешной аутентификации BookFusion открывает Obsidian через protocol handler:

```
obsidian://bookfusion-connect?token={token}
```

| Параметр | Тип | Описание |
|----------|-----|----------|
| `token` | `string` | Токен для заголовка `X-Token` в последующих API-запросах |

---

### POST /obsidian-api/sync

Возвращает страницы книг и индексные файлы для синхронизации с Obsidian vault.

Поддерживает пагинацию через курсор: запросы повторяются с `cursor` из предыдущего ответа, пока `cursor` не станет `null`.

#### Запрос

```http
POST /obsidian-api/sync HTTP/1.1
Host: www.bookfusion.com
Content-Type: application/json
X-Token: tok_abc123def456
API-Version: 1

{
  "cursor": null
}
```

**Заголовки:**

| Заголовок | Значение | Описание |
|-----------|----------|----------|
| `Content-Type` | `application/json` | |
| `X-Token` | `{token}` | Токен аутентификации |
| `API-Version` | `1` | Версия API. Строковое значение `"1"`. |

**Тело запроса:**

| Поле | Тип | Обязательный | Описание |
|------|-----|:---:|----------|
| `cursor` | `string \| null` | да | Курсор пагинации. `null` — начало синхронизации; строка — продолжение. |

#### Ответ `200 OK`

Пример — первая страница с одной книгой:

```json
{
  "pages": [
    {
      "id": "bf-book-123",
      "type": "book",
      "content": "# The Great Gatsby\n\nA story of wealth and loss in the 1920s.",
      "directory": "BookFusion",
      "filename": "The Great Gatsby.md",
      "update_strategy": "magic",
      "frontmatter": "title: The Great Gatsby\nauthor: F. Scott Fitzgerald\nrating: 5",
      "highlights": [
        {
          "id": "hl-456",
          "content": "So we beat on, boats against the current, borne back ceaselessly into the past.",
          "chapter_heading": "## Chapter 9",
          "previous": "hl-455",
          "next": null
        }
      ],
      "atomic_highlights": false
    }
  ],
  "cursor": "eyJpZCI6MTAwfQ==",
  "next_sync_cursor": null
}
```

**Поля ответа:**

| Поле | Тип | Описание |
|------|-----|----------|
| `pages` | `Page[]` | Массив страниц для создания или обновления. Может быть пустым `[]`. |
| `cursor` | `string \| null` | Курсор для следующего запроса текущей сессии. `null` — сессия пагинации завершена. |
| `next_sync_cursor` | `string \| null` | Курсор для следующей сессии синхронизации. Сохранить и передать как `cursor` в первом запросе следующего запуска. `null` — нет нового курсора для сохранения. # UNVERIFIED |

#### Пагинация

```
Сессия 1:
  POST {cursor: null}  → {cursor: "A", next_sync_cursor: null,  pages: [...]}
  POST {cursor: "A"}   → {cursor: "B", next_sync_cursor: null,  pages: [...]}
  POST {cursor: "B"}   → {cursor: null, next_sync_cursor: "Z",  pages: [...]}
  → сессия завершена, сохранить next_sync_cursor = "Z"

Сессия 2:
  POST {cursor: "Z"}   → {cursor: null, next_sync_cursor: "W",  pages: [...]}
  → сессия завершена, сохранить next_sync_cursor = "W"
```

#### Ошибки

| Код | Тело ответа | Описание |
|-----|-------------|----------|
| не 2xx | `{"message": "..."}` | Ошибка сервера |

---

## 5. Структуры данных

Все структуры используются в ответе `POST /obsidian-api/sync`.

### 5.1 Page

Базовый тип. Конкретный тип страницы определяется полем `type`.

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | `"book" \| "index"` | Тип страницы |
| `content` | `string \| null` | Содержимое Markdown-файла |
| `directory` | `string` | Путь к папке в Obsidian vault |
| `filename` | `string` | Имя файла |
| `update_strategy` | `"append" \| "replace" \| "magic" \| "insert"` | Стратегия обновления существующего файла |

**Значения `update_strategy`:**

| Значение | Описание |
|----------|----------|
| `append` | Новые хайлайты добавляются в конец файла |
| `replace` | Файл перезаписывается целиком |
| `magic` | Позиционное обновление по magic-комментариям; использует поля `previous` / `next` хайлайтов |
| `insert` | Позиционное обновление без magic-комментариев |

---

### 5.2 BookPage

Страница книги. Содержит все поля `Page`, плюс:

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | `"book"` | Всегда `"book"` |
| `id` | `string` | ID книги. Используется в magic-комментариях файла (раздел 7). |
| `frontmatter` | `string \| null` | YAML-строка без разделителей `---`. При создании файла вставляется между `---`. `null` — frontmatter отсутствует. |
| `highlights` | `HighlightBlock[] \| AtomicHighlightPage[]` | Массив хайлайтов. Тип элементов определяется полем `atomic_highlights`. |
| `atomic_highlights` | `boolean` | `true` — каждый хайлайт создаётся в отдельном файле (тип `AtomicHighlightPage`). `false` — хайлайты встраиваются в файл книги (тип `HighlightBlock`). |

Полный набор полей `BookPage`:

| Поле | Тип |
|------|-----|
| `type` | `"book"` |
| `content` | `string \| null` |
| `directory` | `string` |
| `filename` | `string` |
| `update_strategy` | `"append" \| "replace" \| "magic" \| "insert"` |
| `id` | `string` |
| `frontmatter` | `string \| null` |
| `highlights` | `HighlightBlock[] \| AtomicHighlightPage[]` |
| `atomic_highlights` | `boolean` |

---

### 5.3 IndexPage

Индексный файл. Содержит все поля `Page` без дополнительных.

| Поле | Тип |
|------|-----|
| `type` | `"index"` |
| `content` | `string \| null` |
| `directory` | `string` |
| `filename` | `string` |
| `update_strategy` | `"append" \| "replace" \| "magic" \| "insert"` |

---

### 5.4 HighlightBlock

Хайлайт, встраиваемый в файл книги. Используется когда `BookPage.atomic_highlights = false`.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | `string` | ID хайлайта. Используется в magic-комментариях (раздел 7). |
| `content` | `string` | Текст хайлайта |
| `chapter_heading` | `string \| null` | Заголовок главы, перед которым отображается хайлайт |
| `previous` | `string \| null` | ID предыдущего хайлайта в документе. Используется стратегиями `magic` и `insert`. |
| `next` | `string \| null` | ID следующего хайлайта в документе. Используется стратегиями `magic` и `insert`. |

---

### 5.5 AtomicHighlightPage

Хайлайт в отдельном файле. Используется когда `BookPage.atomic_highlights = true`. Содержит все поля `HighlightBlock`, плюс:

| Поле | Тип | Описание |
|------|-----|----------|
| `directory` | `string` | Путь к папке в vault для файла хайлайта |
| `filename` | `string` | Имя файла хайлайта |
| `link` | `string` | Obsidian-ссылка на файл хайлайта (встраивается в файл книги) |

Полный набор полей `AtomicHighlightPage`:

| Поле | Тип |
|------|-----|
| `id` | `string` |
| `content` | `string` |
| `chapter_heading` | `string \| null` |
| `previous` | `string \| null` |
| `next` | `string \| null` |
| `directory` | `string` |
| `filename` | `string` |
| `link` | `string` |

---

## 6. Алгоритм calibre_metadata_digest

SHA-256 дайджест метаданных книги, вычисляемый Calibre-плагином. Сервер сохраняет его и возвращает в ответе `GET /uploads/{id}`, чтобы плагин мог определить — изменились ли метаданные с момента последней загрузки.

**Источник:** `calibre-plugin/upload_worker.py:275–322`

Алгоритм — последовательная запись полей в SHA-256 хэш в UTF-8. Поля пропускаются если равны `None` или пустой строке:

1. `title` — всегда
2. `summary` (поле `comments` в Calibre) — если не пустой
3. Первый элемент `metadata.languages` — если список не пустой
4. `isbn` — если не пустой
5. `pubdate.date().isoformat()` — если значение не равно `"0101-01-01"`
6. Для каждой серии из `metadata.series` и кастомных полей типа `series`:
   - `series.title` (UTF-8)
   - `str(series.index)` (UTF-8) — если `series.index is not None`
7. Для каждого автора из `metadata.authors`: `author` (UTF-8)
8. Для каждого тега из `metadata.tags`: `tag` (UTF-8)
9. Для каждой полки из `bookshelves_custom_column` (если настроена): `bookshelf` (UTF-8)
10. Если обложка существует:
    - `bytes(os.path.getsize(cover_path))` — размер файла как Python `bytes`-объект
    - `b'\0'`
    - Содержимое файла обложки блоками по 65536 байт

```python
from hashlib import sha256
import os

h = sha256()
h.update(title.encode('utf-8'))
if summary:
    h.update(summary.encode('utf-8'))
if language:
    h.update(language.encode('utf-8'))
if isbn:
    h.update(isbn.encode('utf-8'))
if issued_on and issued_on != '0101-01-01':
    h.update(issued_on.encode('utf-8'))
for s in series_list:
    h.update(s['title'].encode('utf-8'))
    if s['index'] is not None:
        h.update(str(s['index']).encode('utf-8'))
for author in authors:
    h.update(author.encode('utf-8'))
for tag in tags:
    h.update(tag.encode('utf-8'))
for shelf in bookshelves:
    h.update(shelf.encode('utf-8'))
if cover_path:
    h.update(bytes(os.path.getsize(cover_path)))
    h.update(b'\0')
    with open(cover_path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
digest = h.hexdigest()
```

---

## 7. Magic-комментарии Obsidian

Obsidian-плагин размечает блоки контента специальными комментариями. Это позволяет обновлять отдельные хайлайты без перезаписи всего файла.

**Источник:** `obsidian-plugin/src/utils.ts:3`

**Формат блока:**

```
%%begin-{id}%%
{content}
%%end-{id}%%
```

- `{id}` — значение поля `id` из `BookPage` или `HighlightBlock` / `AtomicHighlightPage`
- При обновлении плагин ищет блок с совпадающим `id` и заменяет его целиком
- Стратегии `magic` и `insert` используют поля `previous` / `next` хайлайтов для определения позиции вставки нового блока

**Пример файла с хайлайтами:**

```markdown
---
title: The Great Gatsby
author: F. Scott Fitzgerald
---

%%begin-bf-book-123%%
# The Great Gatsby

A story of wealth and loss in the 1920s.
%%end-bf-book-123%%

%%begin-hl-456%%
## Chapter 9
So we beat on, boats against the current, borne back ceaselessly into the past.
%%end-hl-456%%
```

---

## 8. Поддерживаемые форматы файлов

**Источник:** `calibre-plugin/book_format.py:7–8`

Calibre-плагин выбирает формат файла для загрузки в следующем порядке:

1. Предпочтительные форматы (проверяются первыми): `EPUB`, `MOBI`
2. Если предпочтительного нет — первый поддерживаемый формат из списка:

`AZW`, `AZW3`, `AZW4`, `CBZ`, `CBR`, `CBC`, `CHM`, `DJVU`, `DOCX`, `EPUB`, `FB2`, `FBZ`, `HTML`, `HTMLZ`, `LIT`, `LRF`, `MOBI`, `ODT`, `PDF`, `PRC`, `PDB`, `PML`, `RB`, `RTF`, `SNB`, `TCR`, `TXT`, `TXTZ`

Если у книги нет файла ни в одном поддерживаемом формате, книга пропускается без загрузки.
