from acasmart.data.repos.reports_repo import fetch_all_contacts
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QHBoxLayout
)
from PySide6.QtCore import Qt
from acasmart.ui.widgets.theme_manager import ThemeManager
from acasmart.ui.widgets.base_secondary_window import BaseSecondaryWindow


class ContactsWindow(BaseSecondaryWindow):
    def __init__(self, return_target: QWidget | None = None):
        super().__init__("📒 دفترچه تلفن", return_target)
        self.setGeometry(300, 200, 700, 500)

        layout = self.content_layout()
        layout.setSpacing(10)

        title = QLabel("📒 لیست شماره تماس هنرجویان و اساتید")
        title.setProperty("sectionTitle", True)
        layout.addWidget(title)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 جستجو بر اساس نام...")
        self.search_input.textChanged.connect(self.apply_filter)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["نام", "کد ملی", "شماره تماس", "نقش"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        for w in (title, self.search_input, self.table):
            try:
                ThemeManager.repolish(w)
            except Exception:
                pass
        self.all_data = []
        self.load_data()
        self.showMaximized()
        self.table.setSortingEnabled(True)

    def load_data(self):
        self.all_data = fetch_all_contacts()
        self.populate_table(self.all_data)

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for row_idx, (name, code, phone, role) in enumerate(data):
            for col_idx, value in enumerate([name, code, phone, role]):
                item = QTableWidgetItem(value or "—")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)

    def apply_filter(self):
        query = self.search_input.text().strip()
        if not query:
            self.populate_table(self.all_data)
        else:
            filtered = [row for row in self.all_data if query in row[0]]
            self.populate_table(filtered)
