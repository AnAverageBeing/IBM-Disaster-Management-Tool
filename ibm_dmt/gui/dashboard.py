from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from ibm_dmt.core.logger import Logger


DASHBOARD_CARD = """
QFrame#card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
}
QFrame#card:hover {
    border-color: #539bf5;
}
"""


class DashboardWidget(QWidget):
    run_backup_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._log = Logger.get_logger()
        self.setStyleSheet(DASHBOARD_CARD)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        title = QLabel("IBM Disaster Management Tool")
        title.setStyleSheet("font-size: 26px; font-weight: 700; color: #e6edf3;")
        layout.addWidget(title)

        subtitle = QLabel("Disaster recovery & business continuity platform")
        subtitle.setStyleSheet("font-size: 14px; color: #8b949e;")
        layout.addWidget(subtitle)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        cards = [
            ("Database Backup", "Run and schedule backups across 8 database engines", "Launch"),
            ("Session History", "View, edit, or delete previous backup sessions", "Open"),
            ("GitHub Sync", "Manage backup uploads to GitHub repositories", "Configure"),
            ("Alert Settings", "Discord, Email, Slack, Telegram, Console", "Settings"),
        ]

        for i, (title_text, desc, btn_text) in enumerate(cards):
            card = self._create_card(title_text, desc, btn_text)
            cards_layout.addWidget(card, i // 2, i % 2)

        layout.addLayout(cards_layout)
        layout.addStretch()

        footer = QLabel()
        footer.setTextFormat(Qt.TextFormat.RichText)
        footer.setText(
            '<span style="color:#484f58;font-size:11px;">'
            'Powered by <a style="color:#539bf5;text-decoration:none;" href="https://studio.pingless.org">PingLess Studios</a>'
            ' &mdash; maintained by AnAverageBeing'
            '</span>'
        )
        footer.setOpenExternalLinks(True)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def _create_card(self, title: str, description: str, btn_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        card_title = QLabel(title)
        card_title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        card_title.setStyleSheet("color: #e6edf3;")
        card_layout.addWidget(card_title)

        card_desc = QLabel(description)
        card_desc.setWordWrap(True)
        card_desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        card_layout.addWidget(card_desc)

        card_layout.addStretch()

        btn = QPushButton(btn_text)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb; border: none; border-radius: 6px;
                padding: 8px 20px; color: #fff; font-weight: 600;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        btn.setFixedWidth(110)
        btn.clicked.connect(lambda: self.run_backup_requested.emit(title))
        card_layout.addWidget(btn)

        return card
