from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QCalendarWidget, QPushButton,
    QComboBox, QSpinBox, QWidget
)
from PySide6.QtGui import QKeySequence,QShortcut,QKeyEvent
from PySide6.QtCore import QDate, Qt,QEvent
import jdatetime
import datetime

# --- Qt compatibility (PySide6 6.0.4 ↔ 6.7.x) ---
try:
    KEY_PRESS = QEvent.Type.KeyPress
except AttributeError:
    KEY_PRESS = QEvent.KeyPress
# -------------------------------------------------


class ShamsiDatePopup(QDialog):
    def __init__(self, parent=None, initial_date=None):
        super().__init__(parent)

        # مقدار اولیه برای تاریخ انتخاب‌شده (به‌صورت شمسی)
        self.selected_date = initial_date or jdatetime.date.today().isoformat()
        self.setWindowTitle("انتخاب تاریخ")
        self.setLayout(QVBoxLayout())

        self.selected_shamsi = None

        # تقویم گرافیکی (QCalendarWidget) برای انتخاب تاریخ میلادی
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)  # نمایش خطوط مشبک در تقویم

        # اگر تاریخ اولیه وجود داشته باشد، تنظیم آن به‌عنوان تاریخ انتخاب‌شده
        if initial_date:
            g_date = jdatetime.date.fromisoformat(initial_date).togregorian()
            self.calendar.setSelectedDate(QDate(g_date.year, g_date.month, g_date.day))
        else:
            self.calendar.setSelectedDate(QDate.currentDate())

        self.layout().addWidget(self.calendar)

        # برچسب برای نمایش معادل تاریخ شمسی
        self.label_shamsi = QLabel()
        self.layout().addWidget(self.label_shamsi)

        # به‌روزرسانی برچسب پس از انتخاب تاریخ جدید
        self.update_shamsi_label()
        self.calendar.selectionChanged.connect(self.update_shamsi_label)

        # دکمه تایید نهایی تاریخ
        btn_ok = QPushButton("تأیید")
        btn_ok.setDefault(True)  # ثبت تاریخ با زدن Enter
        btn_ok.clicked.connect(self.accept)
        self.layout().addWidget(btn_ok)

        # متغیرها برای جعبه‌های انتخاب ماه و سال
        self.month_box = None
        self.year_box = None

        # پیدا کردن ComboBox (ماه) و SpinBox (سال) از داخل QCalendarWidget
        combo_boxes = self.calendar.findChildren(QComboBox)
        spin_boxes = self.calendar.findChildren(QSpinBox)

        if combo_boxes:
            self.month_box = combo_boxes[0]
            self.month_box.installEventFilter(self)  # مدیریت رفتار Enter در ماه

        if spin_boxes:
            self.year_box = spin_boxes[0]
            self.year_box.installEventFilter(self)  # مدیریت رفتار Enter روی سال

        self.calendar.installEventFilter(self)  # بررسی فشردن Enter روی خود تقویم

        # شورتکات‌های سراسری Enter (برای ثبت سریع)
        QShortcut(QKeySequence(Qt.Key_Return), self).activated.connect(self.try_accept)
        QShortcut(QKeySequence(Qt.Key_Enter), self).activated.connect(self.try_accept)

    def update_shamsi_label(self):
        """
        به‌روزرسانی متن برچسب تاریخ شمسی بر اساس انتخاب فعلی در تقویم
        """
        qdate = self.calendar.selectedDate()
        g_date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        j_date = jdatetime.date.fromgregorian(date=g_date)
        self.selected_shamsi = j_date.strftime("%Y-%m-%d")
        self.label_shamsi.setText(f"📅 تاریخ انتخاب‌شده (شمسی): {self.selected_shamsi}")

    def get_selected_date(self):
        """
        خروجی گرفتن تاریخ انتخاب‌شده (به‌صورت شمسی)
        """
        return self.selected_shamsi

    def eventFilter(self, source, event):
        """
        مدیریت فشردن Enter در ویجت‌های سال، ماه و تقویم
        """
        et = event.type()

        if et == KEY_PRESS:
            key = event.key()  # اینجا امنه چون نوع رو چک کردیم
            if key in (Qt.Key_Return, Qt.Key_Enter):
                if source is self.year_box:
                    # اگر فوکوس روی سال است فقط از آن خارج شو
                    self.calendar.setFocus()
                    return True
                elif source is self.month_box:
                    # اگر در ماه Enter زد → تأیید
                    self.accept()
                    return True
                elif self.calendar.hasFocus() or source is self.calendar:
                    # اگر فوکوس روی تقویم است → تأیید در صورت اعتبار
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