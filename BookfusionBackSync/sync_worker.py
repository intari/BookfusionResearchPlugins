__license__ = 'GPL v3'

import json
import logging
import os
import tempfile
import time
import uuid
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

from PyQt5.Qt import QThread, pyqtSignal

from calibre_plugins.bookfusionbacksync.config import prefs

_API_BASE = 'https://bookfusion.com/api'

_GET_HEADERS = {
    'Accept': 'application/json, application/*+json',
    'User-Agent': 'BookFusion/2.22.0 (Android 12; Xiaomi 2201117TG; arm64-v8a)',
}
_POST_HEADERS = {
    **_GET_HEADERS,
    'Content-Type': 'application/json',
}


class SyncWorker(QThread):
    log_message = pyqtSignal(str)
    # progress(current, total): total==0 → marquee (fetch phase); total>0 → percent
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    finished = pyqtSignal(int, int)   # updated, skipped

    def __init__(self, db, library_path=None):
        QThread.__init__(self)
        self.db = db
        self.library_path = library_path
        self._stop = False
        self._log = logging.getLogger('bookfusionbacksync')

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self._sync()
        except Exception as exc:
            self._log.exception('Fatal error in sync')
            self.status.emit(f'Error: {exc}')
            self.log_message.emit(f'Fatal error: {exc}')
            self.finished.emit(0, 0)

    # ── File logging ─────────────────────────────────────────────────────────

    def _setup_logging(self):
        base_path = self.library_path or getattr(self.db, 'library_path', None)
        if not base_path:
            base_path = tempfile.gettempdir()
        log_path = os.path.join(base_path, 'bookfusionbacksync.log')
        logger = logging.getLogger('bookfusionbacksync')
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        fh = logging.FileHandler(log_path, encoding='utf-8')
        fh.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(fh)
        logger.info('─' * 60)
        logger.info('Sync started')
        return logger

    # ── Main flow ────────────────────────────────────────────────────────────

    def _sync(self):
        self._log = self._setup_logging()

        device = prefs['device']
        if not device:
            device = uuid.uuid4().hex[:16]
            prefs['device'] = device
            self._log.info(f'Generated device ID: {device}')

        email    = prefs['email']
        password = prefs['password']
        column   = prefs['last_read_column']
        self._log.info(f'Email: {email}  Column: {column}')

        # 1. Authenticate
        self.status.emit('Authenticating…')
        try:
            token = self._login(device, email, password)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f'Login failed (HTTP {exc.code}) — check email and password in Settings'
            )
        self._emit_log(f'Authenticated as {email}')
        if self._stop:
            return self.finished.emit(0, 0)

        # 2. Fetch all BookFusion books (paginated).
        # Progress bar runs in marquee mode; status label shows running count.
        self.status.emit('Fetching BookFusion library…')
        bf_books = self._fetch_all_books(device, token)
        self._emit_log(f'Fetched {len(bf_books)} books from BookFusion')
        if self._stop:
            return self.finished.emit(0, 0)

        # Build lookups for both id spaces used by BookFusion APIs:
        # - BookV3.id (user library record id)
        # - BookV3.book_id (global uploaded/catalog id, used by official Calibre plugin)
        bf_map_by_id = {}
        bf_map_by_book_id = {}
        bf_all_ids = set()
        bf_all_book_ids = set()
        invalid_date_count = 0
        for book in bf_books:
            bf_id = _id_key(book.get('id'))
            bf_book_id = _id_key(book.get('book_id'))
            if bf_id:
                bf_all_ids.add(bf_id)
            if bf_book_id:
                bf_all_book_ids.add(bf_book_id)

            date_str = book.get('last_read_at')
            source = 'last_read_at'
            if not date_str:
                rp = book.get('reading_position') or {}
                date_str = rp.get('updated_at')
                source = 'reading_position.updated_at'
            if date_str:
                dt = _parse_iso(date_str)
                if dt is None:
                    invalid_date_count += 1
                    continue
                if bf_id:
                    bf_map_by_id[bf_id] = (dt, source)
                if bf_book_id:
                    bf_map_by_book_id[bf_book_id] = (dt, source)

        self._emit_log(
            f'BookFusion date map: by book_id={len(bf_map_by_book_id)}, by id={len(bf_map_by_id)}, '
            f'invalid_dates={invalid_date_count}'
        )
        self._emit_log(
            f'BookFusion ids observed: book_id={len(bf_all_book_ids)}, id={len(bf_all_ids)}'
        )

        # 3. Scan Calibre library (progress bar switches to determinate mode)
        self.status.emit('Scanning Calibre library…')
        calibre_books = self._calibre_books_with_bf_id()
        self._emit_log(
            f'{len(calibre_books)} Calibre books have a BookFusion identifier'
        )

        total = len(calibre_books)
        updates = {}
        skipped = 0
        matched_by_book_id = 0
        matched_by_id = 0
        skipped_no_date = 0
        skipped_not_in_api = 0

        for i, (cal_id, bf_id, title) in enumerate(calibre_books):
            if self._stop:
                break
            self.progress.emit(i, total)

            entry = bf_map_by_book_id.get(bf_id)
            matched_via = 'book_id'
            if entry is None:
                entry = bf_map_by_id.get(bf_id)
                matched_via = 'id'
            if entry is None:
                skipped += 1
                if bf_id in bf_all_book_ids or bf_id in bf_all_ids:
                    skipped_no_date += 1
                    self._log.debug(
                        f'SKIP  {title!r} — found in BookFusion but has no parseable read date '
                        f'(bf_id={bf_id})'
                    )
                else:
                    skipped_not_in_api += 1
                    self._log.debug(f'SKIP  {title!r} — not in BookFusion library (bf_id={bf_id})')
                continue

            dt, source = entry
            if matched_via == 'book_id':
                matched_by_book_id += 1
            else:
                matched_by_id += 1

            updates[cal_id] = dt
            self._emit_log(
                f'OK    {title}  →  {dt.strftime("%Y-%m-%d")}  (from {source}, match={matched_via})'
            )

        if self._stop:
            self.log_message.emit('Sync cancelled.')
            self._log.info('Sync cancelled by user')
            return self.finished.emit(len(updates), skipped)

        # 4. Write all updates to Calibre in one call
        if updates:
            self.status.emit(f'Writing {len(updates)} dates to Calibre…')
            self._log.info(f'Writing {len(updates)} dates to column {column!r}')
            self.db.set_field(column, updates)

        self._log.info(
            'Match stats — '
            f'updated={len(updates)}, matched_by_book_id={matched_by_book_id}, matched_by_id={matched_by_id}, '
            f'skipped_no_date={skipped_no_date}, skipped_not_in_api={skipped_not_in_api}'
        )

        self._log.info(f'Sync finished — {len(updates)} updated, {skipped} skipped')
        self.progress.emit(total, total)
        self.finished.emit(len(updates), skipped)

    # ── HTTP with exponential back-off ───────────────────────────────────────

    def _fetch_json(self, url, post_body=None, timeout=20):
        """GET or POST, returning parsed JSON.

        Retries up to 3 times on network/timeout errors with delays 2 s → 4 s.
        Raises urllib.error.HTTPError immediately (4xx/5xx are not transient).
        """
        headers = _POST_HEADERS if post_body is not None else _GET_HEADERS
        retry_delays = [2, 4]
        last_exc = None

        for attempt in range(3):
            if self._stop:
                raise RuntimeError('Sync stopped')
            method = 'POST' if post_body is not None else 'GET'
            self._log.debug(f'{method} {url}  (attempt {attempt + 1}/3)')
            try:
                req = urllib.request.Request(url, data=post_body, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = resp.read()
                    self._log.debug(f'  → {resp.status}  {len(data)} bytes')
                    return json.loads(data)
            except urllib.error.HTTPError:
                raise   # auth failures, 404, etc. — no retry
            except (urllib.error.URLError, OSError, TimeoutError) as exc:
                last_exc = exc
                self._log.warning(f'  Attempt {attempt + 1}/3 failed: {exc}')
                if attempt < 2:
                    wait = retry_delays[attempt]
                    msg = f'Network error — retrying in {wait}s… ({exc})'
                    self.log_message.emit(msg)
                    self._log.info(f'  Waiting {wait}s before retry')
                    time.sleep(wait)

        raise RuntimeError(f'Failed after 3 attempts: {last_exc}')

    # ── Auth ─────────────────────────────────────────────────────────────────

    def _login(self, device, email, password):
        body = json.dumps(
            {'device': device, 'login': email, 'password': password}
        ).encode('utf-8')
        data = self._fetch_json(f'{_API_BASE}/v1/auth.json', post_body=body)
        return data['token']

    # ── BookFusion library fetch ──────────────────────────────────────────────

    def _fetch_all_books(self, device, token):
        all_books = []
        page = 1
        while not self._stop:
            params = urllib.parse.urlencode({
                'device': device,
                'token': token,
                'page': page,
                'per_page': 100,
            })
            page_data = self._fetch_json(f'{_API_BASE}/v3/library/books.json?{params}')
            if not page_data:
                break
            all_books.extend(page_data)
            self._log.debug(
                f'Page {page}: {len(page_data)} books  (running total: {len(all_books)})'
            )
            # Marquee progress + live count in status bar
            self.progress.emit(len(all_books), 0)
            self.status.emit(f'Fetching BookFusion library… {len(all_books)} books')
            if len(page_data) < 100:
                break
            page += 1
        return all_books

    # ── Calibre helpers ──────────────────────────────────────────────────────

    def _calibre_books_with_bf_id(self):
        result = []
        for cal_id in self.db.all_book_ids():
            ids = self.db.field_for('identifiers', cal_id) or {}
            bf_id = ids.get('bookfusion')
            if bf_id:
                title = self.db.field_for('title', cal_id) or f'Book #{cal_id}'
                result.append((cal_id, str(bf_id), title))
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _emit_log(self, msg, level='info'):
        self.log_message.emit(msg)
        getattr(self._log, level)(msg)


# ── Utility ──────────────────────────────────────────────────────────────────

def _parse_iso(s):
    """Parse ISO 8601 string (Z or +00:00 suffix) into a tz-aware datetime."""
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def _id_key(value):
    if value is None:
        return ''
    return str(value)
