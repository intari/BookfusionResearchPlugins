__license__ = 'GPL v3'

from PyQt5.Qt import (
    QWidget, QVBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox
)
from calibre.utils.config import JSONConfig
from calibre.gui2 import get_current_db

prefs = JSONConfig('plugins/bookfusionbacksync')

prefs.defaults['email'] = ''
prefs.defaults['password'] = ''
prefs.defaults['device'] = ''          # generated on first sync, stored forever
prefs.defaults['last_read_column'] = '#dateread'
prefs.defaults['completed_column'] = ''
prefs.defaults['completed_threshold'] = 99.9
prefs.defaults['fetch_page_size'] = 1980
prefs.defaults['fetch_timeout'] = 90
prefs.defaults['full_skip_logs'] = False
prefs.defaults['ui_batch_logs'] = False


class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        help_label = QLabel(
            '<b>BookFusion Back Sync</b><br>'
            'Reads last-read dates from the BookFusion private API and writes them<br>'
            'to the selected Calibre custom column for books matched by their<br>'
            '<tt>bookfusion</tt> identifier.'
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        layout.addLayout(form)

        self.email = QLineEdit(self)
        self.email.setPlaceholderText('your@email.com')
        self.email.setText(prefs['email'])
        form.addRow('BookFusion Email:', self.email)

        self.password = QLineEdit(self)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText('password')
        self.password.setText(prefs['password'])
        form.addRow('Password:', self.password)

        self.last_read_column = QComboBox(self)
        self.last_read_column.addItem('')
        for key, meta in get_current_db().new_api.field_metadata.custom_iteritems():
            if meta['datatype'] == 'datetime':
                self.last_read_column.addItem(key)
        self.last_read_column.setCurrentText(prefs['last_read_column'])
        form.addRow('Last Read Column:', self.last_read_column)

        self.completed_column = QComboBox(self)
        self.completed_column.addItem('')
        for key, meta in get_current_db().new_api.field_metadata.custom_iteritems():
            if meta['datatype'] == 'bool':
                self.completed_column.addItem(key)
        self.completed_column.setCurrentText(prefs['completed_column'])
        form.addRow('Completed Column (bool):', self.completed_column)

        self.completed_threshold = QDoubleSpinBox(self)
        self.completed_threshold.setRange(0.0, 100.0)
        self.completed_threshold.setDecimals(2)
        self.completed_threshold.setSingleStep(0.1)
        self.completed_threshold.setValue(float(prefs['completed_threshold']))
        form.addRow('Completed Threshold (%):', self.completed_threshold)

        self.fetch_page_size = QSpinBox(self)
        self.fetch_page_size.setRange(10, 50000)
        self.fetch_page_size.setSingleStep(100)
        self.fetch_page_size.setValue(int(prefs['fetch_page_size']))
        form.addRow('Fetch Page Size:', self.fetch_page_size)

        self.fetch_timeout = QSpinBox(self)
        self.fetch_timeout.setRange(5, 600)
        self.fetch_timeout.setSingleStep(5)
        self.fetch_timeout.setValue(int(prefs['fetch_timeout']))
        form.addRow('Fetch Timeout (sec):', self.fetch_timeout)

        self.full_skip_logs = QCheckBox(self)
        self.full_skip_logs.setChecked(bool(prefs['full_skip_logs']))
        form.addRow('Full SKIP Logs:', self.full_skip_logs)

        self.ui_batch_logs = QCheckBox(self)
        self.ui_batch_logs.setChecked(bool(prefs['ui_batch_logs']))
        form.addRow('Batch UI Logs:', self.ui_batch_logs)

        note = QLabel(
            '<small>Only <i>Date</i>-type custom columns are listed.<br>'
            'Optional: select a <i>Yes/No</i> custom column to mark Completed books<br>'
            'when reading percentage in BookFusion is above the threshold.<br>'
            'Batch UI logs groups log updates to reduce UI overhead.<br>'
            'Batch size is dynamic and never exceeds 0.5% of matched books.<br>'
            'Books are matched via the <tt>bookfusion</tt> identifier '
            '(set by the BookFusion Calibre plugin).</small>'
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()

    def save_settings(self):
        prefs['email'] = self.email.text().strip()
        prefs['password'] = self.password.text()
        prefs['last_read_column'] = self.last_read_column.currentText()
        prefs['completed_column'] = self.completed_column.currentText()
        prefs['completed_threshold'] = float(self.completed_threshold.value())
        prefs['fetch_page_size'] = int(self.fetch_page_size.value())
        prefs['fetch_timeout'] = int(self.fetch_timeout.value())
        prefs['full_skip_logs'] = bool(self.full_skip_logs.isChecked())
        prefs['ui_batch_logs'] = bool(self.ui_batch_logs.isChecked())
