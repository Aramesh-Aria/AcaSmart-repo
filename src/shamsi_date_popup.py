from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QCalendarWidget, QPushButton,
    QComboBox, QSpinBox, QWidget
)
from PySide6.QtGui import QKeySequence,QShortcut
from PySide6.QtCore import QDate, Qt
import jdatetime
import datetime

class ShamsiDatePopup(QDialog):
    def __init__(self, parent=None, initial_date=None):
        super().__init__(parent)

        # مقدار اولیه برای تاریخ انتخاب‌شده (به‌صورت شمسی)
        self.selected_date = initial_date or jdatetime.date.today().isoformat()
        self.setWindowTitle("انتخاب تاریخ")
        self.setLayout(QVBoxLayout())

        self.selected_shamsi = None

        # ویجت تقویم میلادی (نمایش و انتخاب تاریخ)
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)  # نمایش خطوط مشبک در تقویم

        # اگر تاریخ اولیه داده شده باشد، روی همان تاریخ تنظیم شود
        if initial_date:
            g_date = jdatetime.date.fromisoformat(initial_date).togregorian()
            self.calendar.setSelectedDate(QDate(g_date.year, g_date.month, g_date.day))
        else:
            self.calendar.setSelectedDate(QDate.currentDate())

        self.layout().addWidget(self.calendar)

        # برچسب برای نمایش معادل تاریخ شمسی
        self.label_shamsi = QLabel()
        self.layout().addWidget(self.label_shamsi)

        self.update_shamsi_label()
        self.calendar.selectionChanged.connect(self.update_shamsi_label)

        # دکمه تأیید انتخاب تاریخ
        btn_ok = QPushButton("تأیید")
        btn_ok.setDefault(True)  # ثبت تاریخ با زدن Enter
        btn_ok.clicked.connect(self.accept)
        self.layout().addWidget(btn_ok)

        # جستجو و ثبت ویجت‌های داخلی انتخاب ماه (QComboBox) و سال (QSpinBox)
        self.month_box = None
        self.year_box = None

        combo_boxes = self.calendar.findChildren(QComboBox)
        spin_boxes = self.calendar.findChildren(QSpinBox)

        if combo_boxes:
            self.month_box = combo_boxes[0]
            self.month_box.installEventFilter(self)  # مدیریت رفتار Enter روی ماه

        if spin_boxes:
            self.year_box = spin_boxes[0]
            self.year_box.installEventFilter(self)  # مدیریت رفتار Enter روی سال

        self.calendar.installEventFilter(self)  # بررسی فشردن Enter روی خود تقویم

        # شورتکات‌های سراسری Enter (برای ثبت سریع)
        QShortcut(QKeySequence(Qt.Key_Return), self).activated.connect(self.try_accept)
        QShortcut(QKeySequence(Qt.Key_Enter), self).activated.connect(self.try_accept)

    def update_shamsi_label(self):
        """
        به‌روزرسانی برچسب نمایشی بر اساس تاریخ انتخاب‌شده در تقویم میلادی
        """
        qdate = self.calendar.selectedDate()
        g_date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        j_date = jdatetime.date.fromgregorian(date=g_date)
        self.selected_shamsi = j_date.strftime("%Y-%m-%d")
        self.label_shamsi.setText(f"📅 تاریخ انتخاب‌شده (شمسی): {self.selected_shamsi}")

    def get_selected_date(self):
        """
        دریافت تاریخ انتخاب‌شده (شمسی) برای استفاده بیرونی
        """
        return self.selected_shamsi

    def eventFilter(self, source, event):
        """
        مدیریت فشردن کلید Enter در ویجت‌های سال، ماه و تقویم
        """
        if event.type() == event.KeyPress and event.key() in [Qt.Key_Return, Qt.Key_Enter]:
            if source == self.year_box:
                # اگر کاربر در فیلد سال Enter زد → فقط از آن خارج شود
                self.calendar.setFocus()
                return True
            elif source == self.month_box:
                # اگر در فیلد ماه Enter زد → تأیید شود
                self.accept()
                return True
            elif self.calendar.hasFocus():
                # اگر فوکوس روی تقویم است → بررسی اعتبار و تأیید
                selected_date = self.calendar.selectedDate()
                if selected_date.isValid():
                    self.accept()
                    return True
        return super().eventFilter(source, event)

    def try_accept(self):
        """
        تلاش برای ثبت تاریخ در صورت فشردن Enter از هر جای پنجره.
        اگر فوکوس روی سال باشد، فقط فوکوس برداشته می‌شود.
        """
        current_widget = self.focusWidget()
        if current_widget == self.year_box:
            self.calendar.setFocus()
            return

        selected_date = self.calendar.selectedDate()
        if selected_date.isValid():
            self.accept()