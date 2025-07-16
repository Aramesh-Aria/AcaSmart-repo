from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,QHBoxLayout

)
from PySide6.QtCore import QDate

from shamsi_date_popup import ShamsiDatePopup
import jdatetime
from datetime import date
class ShamsiDatePicker(QWidget):
    """ فقط popup رو باز می‌کنه، و منطق انتخاب تاریخ، فوکوس و تأیید همه درون ShamsiDatePopup انجام میشه"""
    def __init__(self, label_text=""):
        super().__init__()
        self.layout = QHBoxLayout()
        self.label = QLabel(label_text)
        self.button = QPushButton("📅 انتخاب تاریخ")
        self.selected_gregorian = QDate.currentDate()
        self.selected_shamsi = jdatetime.date.today().strftime("%Y-%m-%d")

        self.button.clicked.connect(self.open_calendar)
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)

    def open_calendar(self):
        popup = ShamsiDatePopup(self, initial_date=self.selected_shamsi)
        if popup.exec_():
            self.selected_shamsi = popup.get_selected_date()
            self.selected_gregorian = popup.calendar.selectedDate()
            self.button.setText(self.selected_shamsi)

    def get_miladi_str(self):
        return self.selected_gregorian.toString("yyyy-MM-dd")

    def set_to_today(self):
        self.selected_gregorian = QDate.currentDate()
        self.selected_shamsi = jdatetime.date.today().strftime("%Y-%m-%d")
        self.button.setText("📅 انتخاب تاریخ")

    def setDate(self, qdate: QDate):
        """
        تنظیم تاریخ به صورت میلادی، و آپدیت تاریخ شمسی و متن دکمه.
        """
        self.selected_gregorian = qdate
        g_date = date(qdate.year(), qdate.month(), qdate.day())
        self.selected_shamsi = jdatetime.date.fromgregorian(date=g_date).strftime("%Y-%m-%d")
        self.button.setText(self.selected_shamsi)
