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

        self.setWindowTitle('BookFusion Back Sync')
        self.resize(560, 420)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.status_label = QLabel('Ready. Press "Sync Now" to start.')
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

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
        self.progress_bar.setValue(0)

        self.worker = SyncWorker(self.gui.current_db.new_api)
        self.worker.log_message.connect(self._on_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_log(self, msg):
        self.log_list.addItem(msg)
        self.log_list.scrollToBottom()

    def _on_progress(self, val, total):
        if total > 0:
            self.progress_bar.setValue(int(val * 100 / total))

    def _on_finished(self, updated, skipped):
        self.sync_btn.setEnabled(True)
        self.settings_btn.setEnabled(True)
        self.status_label.setText(
            f'Done — {updated} updated, {skipped} skipped.'
        )
        self.progress_bar.setValue(100)
        self.gui.library_view.model().refresh()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        QDialog.reject(self)
