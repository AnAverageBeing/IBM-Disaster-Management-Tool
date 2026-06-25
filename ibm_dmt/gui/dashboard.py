from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QSizePolicy,
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
    border-color: #484f58;
}
QLabel#cardValue {
    font-size: 32px;
    font-weight: 700;
    color: #e6edf3;
}
QLabel#cardLabel {
    font-size: 12px;
    color: #8b949e;
    text-transform: uppercase;
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
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Disaster Recovery & Business Continuity Platform")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        cards = [
            ("Database Backup", "Run and schedule backups across 8 database engines", "Launch"),
            ("Session History", "View, edit, or delete previous backup sessions", "Open"),
            ("GitHub Sync", "Manage backup uploads to GitHub repositories", "Configure"),
            ("Alert Settings", "Configure notifications via Discord, Email, Slack, Telegram", "Settings"),
        ]

        for i, (title_text, desc, btn_text) in enumerate(cards):
            card = self._create_card(title_text, desc, btn_text)
            cards_layout.addWidget(card, i // 2, i % 2)

        layout.addLayout(cards_layout)
        layout.addStretch()

    def _create_card(self, title: str, description: str, btn_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        card_title = QLabel(title)
        card_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        card_title.setStyleSheet("color: #e6edf3;")
        card_layout.addWidget(card_title)

        card_desc = QLabel(description)
        card_desc.setWordWrap(True)
        card_desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        card_layout.addWidget(card_desc)

        card_layout.addStretch()

        btn = QPushButton(btn_text)
        btn.setObjectName("primaryButton")
        btn.setFixedWidth(120)
        btn.clicked.connect(lambda: self.run_backup_requested.emit(title))
        card_layout.addWidget(btn)

        return card
