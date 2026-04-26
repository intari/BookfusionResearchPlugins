__license__ = 'GPL v3'

from PyQt5.Qt import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QProgressBar
)

from calibre_plugins.bookfusionbacksync.config import prefs
from calibre_plugins.bookfusionbacksync.sync_worker import SyncWorker


class MainDialog(QDialog):
    def __init__(self, gui, do_user_config):
        QDialog.__init__(self, gui)
        self.gui = gui
        self.do_user_config = do_user_config
        self.worker = None
        self._pending_logs = []
        self._ui_batch_size = None
        self._ui_batch_logs_enabled = False
        self._fetch_percent = -1
        self._sync_percent = -1

        self.setWindowTitle('BookFusion Back Sync')
        self.resize(560, 420)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.status_label = QLabel('Ready. Press "Sync Now" to start.')
        layout.addWidget(self.status_label)

        self.fetch_progress_label = QLabel('Fetch Progress')
        layout.addWidget(self.fetch_progress_label)

        self.fetch_progress_bar = QProgressBar()
        self.fetch_progress_bar.setRange(0, 100)
        self.fetch_progress_bar.setValue(0)
        layout.addWidget(self.fetch_progress_bar)

        self.sync_progress_label = QLabel('Sync Progress')
        layout.addWidget(self.sync_progress_label)

        self.sync_progress_bar = QProgressBar()
        self.sync_progress_bar.setRange(0, 100)
        self.sync_progress_bar.setValue(0)
        layout.addWidget(self.sync_progress_bar)

        self.log_list = QListWidget()
        layout.addWidget(self.log_list)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.settings_btn = QPushButton('Settings')
        self.settings_btn.clicked.connect(self._open_settings)
        btn_layout.addWidget(self.settings_btn)

        btn_layout.addStretch()

        self.sync_btn = QPushButton('Sync Now')
        self.sync_btn.setDefault(True)
        self.sync_btn.clicked.connect(self._start_sync)
        btn_layout.addWidget(self.sync_btn)

        self.close_btn = QPushButton('Close')
        self.close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.close_btn)

    def _open_settings(self):
        self.do_user_config(parent=self)

    def _start_sync(self):
        if not prefs['email'] or not prefs['password']:
            self.status_label.setText('Email and password are required — open Settings.')
            return
        if not prefs['last_read_column']:
            self.status_label.setText('Last Read Column is required — open Settings.')
            return

        self.sync_btn.setEnabled(False)
        self.settings_btn.setEnabled(False)
        self.log_list.clear()
        self.status_label.setText('Starting…')
        self.fetch_progress_bar.setValue(0)
        self.sync_progress_bar.setValue(0)
        self._pending_logs = []
        self._ui_batch_size = None
        self._ui_batch_logs_enabled = bool(prefs['ui_batch_logs'])
        self._fetch_percent = -1
        self._sync_percent = -1

        self.worker = SyncWorker(
            self.gui.current_db.new_api,
            self.gui.current_db.library_path,
        )
        self.worker.log_message.connect(self._on_log)
        self.worker.fetch_progress.connect(self._on_fetch_progress)
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_log(self, msg):
        if self._ui_batch_logs_enabled and self._ui_batch_size:
            self._pending_logs.append(msg)
            if len(self._pending_logs) >= self._ui_batch_size:
                self._flush_log_batch()
            return

        self.log_list.addItem(msg)
        self.log_list.scrollToBottom()

    def _on_progress(self, val, total):
        if self._ui_batch_logs_enabled and total > 0 and self._ui_batch_size is None:
            # Dynamic batch size: never more than 0.5% of total books.
            self._ui_batch_size = max(1, int(total * 0.005))
            if self._pending_logs:
                self._flush_log_batch()

        if total > 0:
            pct = int(val * 100 / total)
            if pct != self._sync_percent:
                self._sync_percent = pct
                self.sync_progress_bar.setValue(pct)

    def _on_fetch_progress(self, val, total):
        if total <= 0:
            return
        pct = int(val * 100 / total)
        if pct != self._fetch_percent:
            self._fetch_percent = pct
            self.fetch_progress_bar.setValue(pct)

    def _on_finished(self, updated, skipped):
        self._flush_log_batch()
        self.sync_btn.setEnabled(True)
        self.settings_btn.setEnabled(True)
        self.status_label.setText(
            f'Done — {updated} updated, {skipped} skipped.'
        )
        self.fetch_progress_bar.setValue(100)
        self.sync_progress_bar.setValue(100)
        self.gui.library_view.model().refresh()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        QDialog.reject(self)

    def _flush_log_batch(self):
        if not self._pending_logs:
            return
        self.log_list.addItems(self._pending_logs)
        self._pending_logs = []
        self.log_list.scrollToBottom()
