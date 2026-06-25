from ibm_dmt.core.disaster_module import DisasterModule
from ibm_dmt.modules.database_backup.gui import DatabaseBackupWidget


class DatabaseBackupModule(DisasterModule):
    name = "Database Backup Management"
    description = "Backup and restore databases with scheduling, compression, encryption, and multi-destination upload"
    icon = "database"
    version = "1.0.0"

    def __init__(self):
        self._widget = None

    def get_widget(self):
        if self._widget is None:
            from ibm_dmt.modules.database_backup.gui import DatabaseBackupWidget
            self._widget = DatabaseBackupWidget()
        return self._widget

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass
