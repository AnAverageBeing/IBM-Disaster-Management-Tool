import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtGui import QPixmap, QFont, QFontDatabase
from PyQt6.QtCore import Qt, QTimer
from ibm_dmt.gui.main_window import MainWindow
from ibm_dmt.core.logger import Logger


class Application(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("IBM Disaster Management Tool")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("IBM-DMT")
        self._log = Logger.get_logger()

        self._setup_fonts()
        self._load_stylesheet()
        self._main_window = None

    def _setup_fonts(self):
        font = QFont("Segoe UI", 10)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.setFont(font)

    def _load_stylesheet(self):
        qss_path = Path(__file__).parent / "resources" / "styles.qss"
        if qss_path.exists():
            with open(qss_path) as f:
                self.setStyleSheet(f.read())

    def run(self):
        self._main_window = MainWindow()
        self._main_window.show()
        self._log.info("IBM-DMT GUI started")
        return self.exec()
