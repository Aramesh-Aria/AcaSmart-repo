from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt,Signal,QDate
from PySide6.QtGui import QColor
import pandas as pd
import jdatetime
from acasmart.ui.widgets.shamsi_date_popup import ShamsiDatePopup
from acasmart.ui.widgets.shamsi_date_picker import ShamsiDatePicker
from datetime import timedelta
from acasmart.data.repos.payments_repo import fetch_payments, delete_payment
from acasmart.data.repos.settings_repo import get_setting
from acasmart.data.repos.classes_repo import fetch_classes
from acasmart.core.utils import format_currency_with_unit
from functools import partial
from acasmart.ui.widgets.theme_manager import ThemeManager
from acasmart.ui.widgets.base_secondary_window import BaseSecondaryWindow

class PaymentReportWindow(BaseSecondaryWindow):
    payment_changed = Signal()  # سیگنال برای اعلام تغییرات پرداخت
    edit_requested = Signal(int)
    def __init__(self, student_id=None, class_id=None, return_target: QWidget | None = None):
        super().__init__("📊 گزارش پرداخت‌ها", return_target)
        self.resize(1300, 650)
        # پیدا کردن مرکز صفحه و جابه‌جا کردن پنجره
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

        self.student_id = student_id
        self.class_id = class_id

        layout = self.content_layout()

        # --- فیلتر ها ---
        filter_layout = QHBoxLayout()
        self.input_min_amount = QLineEdit()
        self.input_min_amount.setPlaceholderText("حداقل مبلغ")
        self.input_max_amount = QLineEdit()
        self.input_max_amount.setPlaceholderText("حداکثر مبلغ")
        self.input_student_name = QLineEdit()
        self.input_student_name.setPlaceholderText("نام هنرجو")
        self.combo_class = QComboBox()
        self.combo_class.addItem("همه کلاس‌ها", None)
        for cid, cname, *_ in fetch_classes():
            self.combo_class.addItem(cname, cid)
        self.input_keyword = QLineEdit()
        self.input_keyword.setPlaceholderText("جستجو در توضیحات")
        self.combo_filter_ptype = QComboBox()
        self.combo_filter_ptype.addItems(["همه", "شهریه", "مازاد"])

        # تاریخ‌ها
        self.date_from = ShamsiDatePicker(": از تاریخ")
        self.date_to = ShamsiDatePicker(": تا تاریخ")

        # تنظیم پیش‌فرض بازه تاریخ
        today = jdatetime.date.today()
        three_months_ago = today - jdatetime.timedelta(days=90)
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        self.date_to.setDate(QDate.currentDate())

        filter_layout.addWidget(self.input_min_amount)
        filter_layout.addWidget(self.input_max_amount)
        filter_layout.addWidget(self.input_student_name)
        filter_layout.addWidget(self.combo_class)
        filter_layout.addWidget(self.input_keyword)
        filter_layout.addWidget(self.combo_filter_ptype)
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(self.date_to)

        layout.addLayout(filter_layout)

        # --- دکمه‌ها ---
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("🧹 پاکسازی فیلتر")
        self.btn_clear.setProperty("variant", "secondary")
        self.btn_export = QPushButton("📥 خروجی اکسل")
        self.btn_export.setProperty("variant", "primary")
        self.btn_clear.clicked.connect(self.clear_filters)
        self.btn_export.clicked.connect(self.export_to_excel)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_export)
        layout.addLayout(btn_layout)

        # --- جدول ---
        self.table_payments = QTableWidget()
        self.table_payments.setColumnCount(8)
        self.table_payments.setHorizontalHeaderLabels(
            ["ID", "هنرجو", "کلاس", "مبلغ", "تاریخ پرداخت", "توضیحات", "نوع پرداخت", "عملیات"]
        )
        self.table_payments.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_payments.verticalHeader().setVisible(False)
        self.table_payments.setAlternatingRowColors(True)
        layout.addWidget(self.table_payments)

        # --- مجموع ---
        self.lbl_total_filtered = QLabel("مجموع پرداخت‌های نمایشی: 0 تومان")
        self.lbl_total_filtered.setStyleSheet("font-size:13px; color:green; margin-top:5px;")
        layout.addWidget(self.lbl_total_filtered)
        # Apply QSS to filters/buttons/table
        for w in (
            self.input_min_amount, self.input_max_amount, self.input_student_name, self.combo_class,
            self.input_keyword, self.combo_filter_ptype, self.date_from, self.date_to,
            self.btn_clear, self.btn_export, self.table_payments, self.lbl_total_filtered,
        ):
            try:
                ThemeManager.repolish(w)
            except Exception:
                pass

        # اتصال تغییرات ورودی‌ها به فیلتر زنده
        self.input_min_amount.textChanged.connect(self.load_payments)
        self.input_max_amount.textChanged.connect(self.load_payments)
        self.input_student_name.textChanged.connect(self.load_payments)
        self.combo_class.currentIndexChanged.connect(self.load_payments)
        self.input_keyword.textChanged.connect(self.load_payments)
        self.combo_filter_ptype.currentIndexChanged.connect(self.load_payments)
        self.date_from.button.clicked.connect(self.load_payments)
        self.date_to.button.clicked.connect(self.load_payments)

        self.load_payments()

    def load_payments(self):
        date_from = self.date_from.selected_shamsi
        date_to = self.date_to.selected_shamsi
        class_id = self.combo_class.currentData()
        raw = fetch_payments(
            student_id=self.student_id,
            class_id=self.class_id,
            date_from=date_from,
            date_to=date_to
        )

        filtered = []
        min_amt = self._to_int(self.input_min_amount.text())
        max_amt = self._to_int(self.input_max_amount.text())
        student_kw = self.input_student_name.text().strip().lower()

        desc_kw = self.input_keyword.text().strip().lower()
        sel_ptype = self.combo_filter_ptype.currentText()

        # تاریخ فیلتر
        date_from_g = jdatetime.date.fromisoformat(self.date_from.selected_shamsi).togregorian()
        date_to_g = jdatetime.date.fromisoformat(self.date_to.selected_shamsi).togregorian()

        for row in raw:
            if len(row) < 7:
                continue
            pid, sname, cname, amount, pdate, desc, ptype, row_class_id = row
            try:
                pdate_j = jdatetime.date.fromisoformat(pdate)
                pdate_g = pdate_j.togregorian()
                jdate = pdate_j.strftime("%Y/%m/%d")
            except:
                        # اگر تاریخ پرداخت درست نبود، ردش کن
                continue

            if min_amt is not None and amount < min_amt: continue
            if max_amt is not None and amount > max_amt: continue
            if student_kw and student_kw not in sname.lower(): continue
            if class_id and row_class_id != class_id:
                continue
            if desc_kw and (not desc or desc_kw not in desc.lower()): continue
            if sel_ptype != "همه":
                if sel_ptype == "شهریه" and ptype != 'tuition': continue
                if sel_ptype == "مازاد" and ptype != 'extra': continue

            if pdate_g < date_from_g or pdate_g > date_to_g:
                continue

            filtered.append((pid, sname, cname, amount, jdate, desc, "شهریه" if ptype == 'tuition' else "مازاد"))


        total_displayed = sum([row[3] for row in filtered])
        self.lbl_total_filtered.setText(
            f"مجموع پرداخت‌های نمایشی: {format_currency_with_unit(total_displayed)} — تعداد: {len(filtered)} مورد"
        )

        self.table_payments.setRowCount(0)
        for row_data in filtered:
            row = self.table_payments.rowCount()
            self.table_payments.insertRow(row)

            # ستون‌های معمولی
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                 # ستون مبلغ (col == 3)
                if col == 3:
                    display_value = format_currency_with_unit(value)
                else:
                    display_value = str(value)

                item = QTableWidgetItem(display_value)

                if col == 6:  # نوع پرداخت
                    if value == "مازاد":
                        item.setBackground(QColor("#FFD54F"))
                    else:
                        item.setBackground(QColor("#81C784"))
                self.table_payments.setItem(row, col, item)

            # ستون عملیات
            pid = row_data[0]
            btn_delete = QPushButton("❌ حذف")
            btn_delete.setProperty("variant", "ghost")
            btn_delete.clicked.connect(partial(self.delete_payment, pid))

            btn_edit = QPushButton("✏️ ویرایش")
            btn_edit.setProperty("variant", "secondary")
            btn_edit.clicked.connect(partial(self.edit_payment, pid))

            op_layout = QHBoxLayout()
            op_layout.addWidget(btn_edit)
            op_layout.addWidget(btn_delete)
            op_layout.setContentsMargins(0, 0, 0, 0)

            # Repolish operation buttons
            try:
                ThemeManager.repolish(btn_delete)
                ThemeManager.repolish(btn_edit)
            except Exception:
                pass

            op_widget = QWidget()
            op_widget.setLayout(op_layout)
            self.table_payments.setCellWidget(row, 7, op_widget)

    def clear_filters(self):
        # پاک کردن فیلترهای متنی و انتخاب‌ها
        self.input_min_amount.clear()
        self.input_max_amount.clear()
        self.input_student_name.clear()
        self.combo_class.setCurrentIndex(0)
        self.input_keyword.clear()
        self.combo_filter_ptype.setCurrentIndex(0)

        # بازه پیش‌فرض تاریخ: از سه ماه پیش تا امروز
        today_j = jdatetime.date.today()
        three_months_ago_j = today_j - jdatetime.timedelta(days=90)

        # بازه پیش‌فرض تاریخ: از سه ماه پیش تا امروز
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        self.date_to.setDate(QDate.currentDate())

        # بارگذاری مجدد داده‌ها با بازه پیش‌فرض
        self.load_payments()
        
    def _to_int(self, text):
        try:
            return int(text)
        except:
            return None

    def export_to_excel(self):
        row_count = self.table_payments.rowCount()
        col_count = self.table_payments.columnCount()

        if row_count == 0:
            return

        data = []
        headers = [self.table_payments.horizontalHeaderItem(col).text() for col in range(col_count)]
        for row in range(row_count):
            row_data = []
            for col in range(col_count):
                item = self.table_payments.item(row, col)
                row_data.append(item.text() if item else "")
            data.append(row_data)

        df = pd.DataFrame(data, columns=headers)
        filename = f"پرداخت‌ها_{jdatetime.date.today()}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل اکسل", filename, "Excel Files (*.xlsx)")
        if file_path:
            df.to_excel(file_path, index=False)

    def delete_payment(self, payment_id):
        reply = QMessageBox.question(self, "حذف پرداخت", "آیا مطمئن هستید؟")
        if reply == QMessageBox.Yes:
            delete_payment(payment_id)
            self.load_payments()
            self.payment_changed.emit()  # ارسال سیگنال تغییر

    def edit_payment(self, payment_id):
        # اعلام به والد (PaymentManager) که این پرداخت باید برای ویرایش لود شود
        self.edit_requested.emit(payment_id)
        # ترجیحاً این پنجره بسته شود تا کاربر مستقیماً روی فرم ویرایش باشد:
        self.close()
