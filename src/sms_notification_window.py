from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget,
    QListWidgetItem, QHBoxLayout, QMessageBox, QCheckBox, QScrollArea
)
from PyQt5.QtCore import Qt
from db_helper import fetch_students
from sms_notifier import SmsNotifier

class SmsNotificationWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📲 ارسال پیامک به هنرجویان")
        self.setGeometry(300, 200, 500, 600)
        self.students = []
        self.checkboxes = []
        self.notifier = SmsNotifier()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(2)
        layout.setContentsMargins(5, 5, 5, 5)

        title = QLabel("📨 ارسال پیامک به هنرجویان")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 17px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 جستجوی هنرجو بر اساس نام...")
        self.search_input.textChanged.connect(self.filter_students)
        self.search_input.setStyleSheet("padding: 6px;")
        layout.addWidget(self.search_input)

        # دکمه انتخاب همه / لغو همه
        select_all_btn = QPushButton("✔️ انتخاب همه / لغو همه")
        select_all_btn.clicked.connect(self.toggle_select_all)
        select_all_btn.setStyleSheet("padding: 6px;")
        layout.addWidget(select_all_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(400)  # محدود کردن ارتفاع
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout()
        self.list_layout.setSpacing(4)
        self.list_container.setLayout(self.list_layout)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)

        self.btn_send_sms = QPushButton("📤 ارسال پیامک برای انتخاب‌شده‌ها")
        self.btn_send_sms.clicked.connect(self.send_sms_to_selected)
        self.btn_send_sms.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        layout.addWidget(self.btn_send_sms)

        self.setLayout(layout)
        self.load_students()

    def toggle_select_all(self):
        all_selected = all(cb.isChecked() for cb in self.checkboxes)
        for cb in self.checkboxes:
            cb.setChecked(not all_selected)

    def load_students(self):
        self.students = fetch_students()
        self.refresh_student_list()

    def refresh_student_list(self, filtered=None):
        for i in reversed(range(self.list_layout.count())):
            self.list_layout.itemAt(i).widget().setParent(None)
        self.checkboxes.clear()

        data = filtered if filtered is not None else self.students
        for sid, name, gender, birth_date, national_code in data:
            cb = QCheckBox(f"{name} - کدملی: {national_code}")
            cb.setProperty("student_id", sid)
            cb.setStyleSheet("padding: 2px; font-size: 13px;")
            self.checkboxes.append(cb)
            self.list_layout.addWidget(cb)

    def filter_students(self):
        text = self.search_input.text().strip().lower()
        if not text:
            self.refresh_student_list()
            return
        filtered = [s for s in self.students if text in s[1].lower()]
        self.refresh_student_list(filtered)

    def send_sms_to_selected(self):
        selected = [cb for cb in self.checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "هیچ انتخابی", "لطفاً حداقل یک هنرجو را انتخاب کنید.")
            return

        count = 0
        for cb in selected:
            student_id = cb.property("student_id")
            name, phone = self.get_student_contact(student_id)
            if name and phone:
                try:
                    self.notifier.send_renew_term_notification(name, phone, "کلاس موسیقی")
                    count += 1
                except Exception as e:
                    print(e)
        QMessageBox.information(self, "پایان عملیات", f"ارسال پیامک برای {count} هنرجو انجام شد.")

    def get_student_contact(self, student_id):
        from db_helper import get_student_contact
        return get_student_contact(student_id)
