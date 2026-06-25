from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QStackedWidget, QLabel, QListWidget,
    QListWidgetItem, QFrame, QStatusBar, QMessageBox, QSplitter,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from ibm_dmt.core.plugin_manager import PluginManager
from ibm_dmt.core.logger import Logger
from ibm_dmt.gui.dashboard import DashboardWidget
from ibm_dmt.gui.session_manager import SessionManagerDialog


SIDEBAR_STYLE = """
QWidget#sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
    min-width: 240px;
    max-width: 240px;
}
QPushButton#navButton {
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 0;
    background-color: transparent;
    font-size: 13px;
    color: #8b949e;
}
QPushButton#navButton:hover {
    background-color: #1c2128;
    color: #e6edf3;
}
QPushButton#navButton:checked {
    background-color: #1f6feb22;
    color: #e6edf3;
    border-left: 3px solid #1f6feb;
}
QPushButton#headerButton {
    text-align: left;
    padding: 16px;
    border: none;
    border-radius: 0;
    background-color: transparent;
    font-size: 16px;
    font-weight: 700;
    color: #e6edf3;
}
QPushButton#headerButton:hover {
    background-color: #1c2128;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._log = Logger.get_logger()
        self._plugin_manager = PluginManager()
        self._modules = {}
        self._nav_buttons = []
        self._init_ui()
        self._discover_modules()

    def _init_ui(self):
        self.setWindowTitle("IBM Disaster Management Tool")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(SIDEBAR_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        header = QPushButton("IBM-DMT")
        header.setObjectName("headerButton")
        sidebar_layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #30363d;")
        sidebar_layout.addWidget(sep)

        self._nav_list = QWidget()
        self._nav_layout = QVBoxLayout(self._nav_list)
        self._nav_layout.setContentsMargins(0, 0, 0, 0)
        self._nav_layout.setSpacing(0)
        self._nav_layout.addStretch()
        sidebar_layout.addWidget(self._nav_list)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #30363d;")
        sidebar_layout.addWidget(sep2)

        session_btn = QPushButton("Manage Sessions")
        session_btn.setObjectName("navButton")
        session_btn.clicked.connect(self._open_session_manager)
        sidebar_layout.addWidget(session_btn)

        main_layout.addWidget(sidebar)

        self._content_stack = QStackedWidget()
        main_layout.addWidget(self._content_stack, 1)

        self._dashboard = DashboardWidget()
        self._dashboard.run_backup_requested.connect(self._switch_to_module)
        self._content_stack.addWidget(self._dashboard)
        self._content_stack.setCurrentWidget(self._dashboard)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _discover_modules(self):
        modules = self._plugin_manager.discover_modules()
        for name, module in modules.items():
            btn = QPushButton(module.icon + "  " + name)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, m=name: self._switch_to_module(m))
            self._nav_layout.insertWidget(self._nav_layout.count() - 1, btn)
            self._nav_buttons.append(btn)

            widget = module.get_widget()
            self._content_stack.addWidget(widget)
            self._modules[name] = module

    def _switch_to_module(self, module_name: str):
        for btn in self._nav_buttons:
            btn.setChecked(False)

        sender = self.sender()
        if isinstance(sender, QPushButton):
            sender.setChecked(True)

        module = self._modules.get(module_name) or self._plugin_manager.get_module(module_name)
        if module:
            self._content_stack.setCurrentWidget(module.get_widget())
            self.status_bar.showMessage(f"Active Module: {module_name}")

    def _open_session_manager(self):
        dialog = SessionManagerDialog(self)
        dialog.exec()
