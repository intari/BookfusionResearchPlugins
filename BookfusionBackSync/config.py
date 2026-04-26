__license__ = 'GPL v3'

from PyQt5.Qt import (
    QWidget, QVBoxLayout, QFormLayout, QLabel,
    QLineEdit, QComboBox
)
from calibre.utils.config import JSONConfig
from calibre.gui2 import get_current_db

prefs = JSONConfig('plugins/bookfusionbacksync')

prefs.defaults['email'] = ''
prefs.defaults['password'] = ''
prefs.defaults['device'] = ''          # generated on first sync, stored forever
prefs.defaults['last_read_column'] = '#dateread'


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

        note = QLabel(
            '<small>Only <i>Date</i>-type custom columns are listed.<br>'
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
