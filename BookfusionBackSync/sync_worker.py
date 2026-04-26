__license__ = 'GPL v3'

import json
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
    progress = pyqtSignal(int, int)   # current, total
    status = pyqtSignal(str)
    finished = pyqtSignal(int, int)   # updated, skipped

    def __init__(self, db):
        QThread.__init__(self)
        self.db = db          # calibre new_api (Cache)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self._sync()
        except Exception as exc:
            self.status.emit(f'Error: {exc}')
            self.log_message.emit(f'Fatal error: {exc}')
            self.finished.emit(0, 0)

    # ── Main sync flow ───────────────────────────────────────────────────────

    def _sync(self):
        # Ensure a stable device ID exists
        device = prefs['device']
        if not device:
            device = uuid.uuid4().hex[:16]
            prefs['device'] = device

        email = prefs['email']
        password = prefs['password']
        column = prefs['last_read_column']

        # 1. Authenticate
        self.status.emit('Authenticating…')
        try:
            token = self._login(device, email, password)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f'Login failed (HTTP {exc.code}) — check email and password in Settings'
            )
        self.log_message.emit(f'Authenticated as {email}')
        if self._stop:
            return self.finished.emit(0, 0)

        # 2. Fetch all BookFusion books (paginated)
        self.status.emit('Fetching BookFusion library…')
        bf_books = self._fetch_all_books(device, token)
        self.log_message.emit(f'Fetched {len(bf_books)} books from BookFusion')
        if self._stop:
            return self.finished.emit(0, 0)

        # Build lookup: str(BookV3.id) → (date_str, source_field_name)
        # Primary source: last_read_at
        # Fallback: reading_position.updated_at (more commonly populated)
        bf_map = {}
        for book in bf_books:
            bf_id = str(book.get('id', ''))
            if not bf_id:
                continue
            date_str = book.get('last_read_at')
            source = 'last_read_at'
            if not date_str:
                rp = book.get('reading_position') or {}
                date_str = rp.get('updated_at')
                source = 'reading_position.updated_at'
            if date_str:
                bf_map[bf_id] = (date_str, source)

        self.log_message.emit(
            f'{len(bf_map)} of {len(bf_books)} books have a read date in BookFusion'
        )

        # 3. Collect Calibre books that carry a bookfusion identifier
        self.status.emit('Scanning Calibre library…')
        calibre_books = self._calibre_books_with_bf_id()
        self.log_message.emit(
            f'{len(calibre_books)} Calibre books have a BookFusion identifier'
        )

        total = len(calibre_books)
        updates = {}
        skipped = 0

        for i, (cal_id, bf_id, title) in enumerate(calibre_books):
            if self._stop:
                break
            self.progress.emit(i, total)

            entry = bf_map.get(bf_id)
            if entry is None:
                skipped += 1
                continue

            date_str, source = entry
            dt = _parse_iso(date_str)
            if dt is None:
                skipped += 1
                self.log_message.emit(f'SKIP  {title} — unparseable date {date_str!r}')
                continue

            updates[cal_id] = dt
            self.log_message.emit(
                f'OK    {title}  →  {dt.strftime("%Y-%m-%d")}  (from {source})'
            )

        if self._stop:
            self.log_message.emit('Sync cancelled.')
            return self.finished.emit(len(updates), skipped)

        # 4. Write all updates to Calibre in a single call
        if updates:
            self.status.emit(f'Writing {len(updates)} dates to Calibre…')
            self.db.set_field(column, updates)

        self.progress.emit(total, total)
        self.finished.emit(len(updates), skipped)

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    def _login(self, device, email, password):
        body = json.dumps(
            {'device': device, 'login': email, 'password': password}
        ).encode('utf-8')
        req = urllib.request.Request(
            f'{_API_BASE}/v1/auth.json',
            data=body,
            headers=_POST_HEADERS,
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())['token']

    def _fetch_all_books(self, device, token):
        all_books = []
        page = 1
        while not self._stop:
            params = urllib.parse.urlencode({
                'device': device,
                'token': token,
                'page': page,
                'per_page': 100,
                'sort': 'last_read_at-desc',
            })
            req = urllib.request.Request(
                f'{_API_BASE}/v3/library/books.json?{params}',
                headers=_GET_HEADERS,
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                page_data = json.loads(resp.read())
            if not page_data:
                break
            all_books.extend(page_data)
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


# ── Utility ──────────────────────────────────────────────────────────────────

def _parse_iso(s):
    """Parse ISO 8601 string with trailing Z or +00:00 into a tz-aware datetime."""
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None
