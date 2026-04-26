__license__ = 'GPL v3'

from calibre.customize import InterfaceActionBase


class BookFusionBackSyncPlugin(InterfaceActionBase):
    name = 'BookFusion Back Sync'
    description = 'Sync last-read dates from BookFusion back into Calibre custom columns.'
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'Dmitriy Kazimirov'
    version = (0, 0, 4)
    minimum_calibre_version = (6, 2, 1)

    actual_plugin = 'calibre_plugins.bookfusionbacksync.ui:InterfacePlugin'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.bookfusionbacksync.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
        ac = self.actual_plugin_
        if ac is not None:
            ac.apply_settings()
