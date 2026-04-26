__license__ = 'GPL v3'

from calibre.gui2.actions import InterfaceAction
from calibre_plugins.bookfusionbacksync.main import MainDialog


class InterfacePlugin(InterfaceAction):
    name = 'BookFusion Back Sync'

    action_spec = (
        'BookFusion Back Sync', None,
        'Sync last-read dates from BookFusion to Calibre', None
    )

    def genesis(self):
        try:
            self.qaction.setIcon(get_icons('images/icon.png'))
        except Exception:
            pass
        self.qaction.triggered.connect(self.show_dialog)

    def show_dialog(self):
        base_plugin_object = self.interface_action_base_plugin
        do_user_config = base_plugin_object.do_user_config
        MainDialog(self.gui, do_user_config).show()

    def apply_settings(self):
        pass
