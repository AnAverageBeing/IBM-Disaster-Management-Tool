import sys
import os


def main():
    if "--headless" in sys.argv:
        _run_headless()
    else:
        _run_gui()


def _run_gui():
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print("Error: PyQt6 is required. Run the installer or: pip install PyQt6")
        sys.exit(1)

    from ibm_dmt.gui.app import Application
    from ibm_dmt.core.alert_manager import AlertManager
    from ibm_dmt.core.logger import Logger

    Logger()
    AlertManager().register_default_handlers()

    app = Application(sys.argv)
    sys.exit(app.run())


def _run_headless():
    import json
    from ibm_dmt.core.logger import Logger
    from ibm_dmt.core.alert_manager import AlertManager
    from ibm_dmt.modules.database_backup.backup_engine import BackupEngine

    Logger()
    AlertManager().register_default_handlers()

    config_path = None
    if len(sys.argv) > 2 and sys.argv[1] == "--config":
        config_path = sys.argv[2]

    if not config_path or not os.path.exists(config_path):
        print("Usage: ibm-dmt --headless --config <config.json>")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    engine = BackupEngine()
    result = engine.run_backup(config)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "completed" else 1)


if __name__ == "__main__":
    main()
