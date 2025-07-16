from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QDateEdit, QTextEdit, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QFileDialog, QFormLayout
)
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QIntValidator, QColor

from datetime import datetime, date
from db_helper import (
    fetch_students_with_teachers, fetch_classes,
    insert_payment, fetch_payments, get_total_paid_for_term, delete_payment, get_setting,
    count_attendance, fetch_teachers_simple,get_student_term,fetch_extra_payments_for_term,
    get_term_id_by_student_and_class,count_attendance_for_term,fetch_registered_classes_for_student,
    update_payment_by_id
)
from shamsi_date_popup import ShamsiDatePopup
from shamsi_date_picker import ShamsiDatePicker
import jdatetime
from utils import format_currency_with_unit ,get_currency_unit,format_currency
import pandas as pd


class PaymentManager(QWidget):
    pass

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ثبت پرداخت‌ها و گزارش‌گیری مالی")
        self.setGeometry(300, 200, 700, 700)
        self.showMaximized()

        self.last_payment_date = QDate.currentDate()
        self.term_fee = int(get_setting("term_fee", 6000000))
        self.term_start = None
        self.term_end = None
        self.term_expired = True
        self.term_missing = False

        self.selected_student_id = None
        self.selected_student_teacher = None
        self.selected_class_id = None
        self.students = []
        self.classes = []
        self.is_editing = False
        self.editing_payment_id = None
        self.skip_next_edit = False

        layout = QVBoxLayout()

        # ---------- فیلتر اولیه ----------
        layout.addWidget(QLabel("جستجوی هنرجو:"))
        self.input_search_student = QLineEdit()
        self.input_search_student.setPlaceholderText("نام یا استاد...")
        self.input_search_student.textChanged.connect(self.search_students)
        layout.addWidget(self.input_search_student)

        self.list_students = QListWidget()
        self.list_students.itemClicked.connect(self.select_student)
        layout.addWidget(self.list_students)

        layout.addWidget(QLabel("انتخاب کلاس مرتبط:"))
        self.list_classes = QListWidget()
        self.list_classes.itemClicked.connect(self.select_class)
        layout.addWidget(self.list_classes)

        # ---------- فرم پرداخت ----------
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)

        int_validator = QIntValidator(0, 1000000000)

        self.input_amount = QLineEdit(str(self.term_fee))
        self.input_amount.setValidator(int_validator)
        form_layout.addRow("💰 مبلغ پرداختی:", self.input_amount)

        self.date_payment_picker = ShamsiDatePicker()
        self.date_payment_picker.setDate(self.last_payment_date)  # استفاده از مقدار ذخیره‌شده
        form_layout.addRow("📅 تاریخ پرداخت:", self.date_payment_picker)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["شهریه", "مازاد"])
        form_layout.addRow("📂 نوع پرداخت:", self.combo_type)

        self.input_description = QTextEdit()
        self.input_description.setPlaceholderText("مثلاً بابت ثبت‌نام ترم زمستان...")
        self.input_description.setFixedHeight(60)
        form_layout.addRow("📝 توضیحات:", self.input_description)

        layout.addLayout(form_layout)
        layout.addSpacing(8)

        # ---------- دکمه‌های پرداخت ----------
        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("🧹 پاک‌سازی فرم")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #d5d5d5;
            }
        """)

        self.btn_clear.clicked.connect(self.clear_form)

        self.btn_add_payment = QPushButton("✅ ثبت پرداخت")
        self.set_payment_button_enabled(False)

        self.btn_add_payment.clicked.connect(self.add_payment)

        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_add_payment)
        layout.addLayout(btn_layout)

        # ---------- خلاصه مالی ----------
        self.lbl_total = QLabel("مجموع پرداخت شده: " + format_currency_with_unit(0))
        self.lbl_total.setStyleSheet("font-size:13px; color:gray;")
        layout.addWidget(self.lbl_total)

        self.lbl_remaining = QLabel(f"باقی‌مانده شهریه (ترم جاری): {format_currency_with_unit(self.term_fee)}")
        self.lbl_remaining.setStyleSheet("font-size:13px; color:gray; margin-bottom:10px;")
        layout.addWidget(self.lbl_remaining)

        # ---------- فیلترهای تاریخی ----------
        df_layout = QHBoxLayout()
        self.date_from_picker = ShamsiDatePicker("از تاریخ")
        self.date_to_picker = ShamsiDatePicker("تا تاریخ")
        df_layout.addWidget(self.date_from_picker)
        df_layout.addWidget(self.date_to_picker)
        layout.addLayout(df_layout)

        # ---------- فیلتر پیشرفته ----------
        self.btn_advanced = QPushButton("فیلتر پیشرفته 🔽")
        self.btn_advanced.clicked.connect(self.toggle_advanced)
        layout.addWidget(self.btn_advanced)

        self.adv_widget = QWidget()
        adv = QVBoxLayout()

        amt_layout = QHBoxLayout()
        amt_layout.addWidget(QLabel(": حداقل مبلغ"))
        self.input_min_amount = QLineEdit()
        self.input_min_amount.setValidator(int_validator)
        amt_layout.addWidget(self.input_min_amount)
        amt_layout.addWidget(QLabel(": حداکثر مبلغ"))
        self.input_max_amount = QLineEdit()
        self.input_max_amount.setValidator(int_validator)
        amt_layout.addWidget(self.input_max_amount)
        adv.addLayout(amt_layout)

        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel(": جستجو در توضیحات"))
        self.input_keyword = QLineEdit()
        desc_layout.addWidget(self.input_keyword)
        adv.addLayout(desc_layout)

        ptype_layout = QHBoxLayout()
        ptype_layout.addWidget(QLabel(": نوع پرداخت"))
        self.combo_filter_ptype = QComboBox()
        self.combo_filter_ptype.addItem("همه")
        self.combo_filter_ptype.addItem("شهریه")
        self.combo_filter_ptype.addItem("مازاد")
        ptype_layout.addWidget(self.combo_filter_ptype)
        adv.addLayout(ptype_layout)

        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel(": کلاس"))
        self.combo_filter_class = QComboBox()
        class_layout.addWidget(self.combo_filter_class)
        adv.addLayout(class_layout)

        global_layout = QHBoxLayout()
        global_layout.addWidget(QLabel(": جستجوی کلی"))
        self.input_search_all = QLineEdit()
        global_layout.addWidget(self.input_search_all)
        adv.addLayout(global_layout)

        self.adv_widget.setLayout(adv)
        layout.addWidget(self.adv_widget)
        self.adv_widget.hide()

        # ---------- دکمه‌های گزارش ----------
        report_layout = QHBoxLayout()
        self.btn_filter = QPushButton("🔍 فیلتر گزارش")
        self.btn_filter.clicked.connect(self.load_payments)
        self.btn_export = QPushButton("📥 خروجی اکسل")
        self.btn_export.clicked.connect(self.export_to_excel)
        report_layout.addWidget(self.btn_filter)
        report_layout.addWidget(self.btn_export)
        layout.addLayout(report_layout)

        # ---------- جدول پرداخت ----------
        self.table_payments = QTableWidget()
        self.table_payments.setColumnCount(7)
        self.table_payments.setHorizontalHeaderLabels([
            "ID", "هنرجو", "کلاس", "مبلغ", "تاریخ پرداخت", "توضیحات", "نوع پرداخت"
        ])
        self.table_payments.verticalHeader().setVisible(False)  # مخفی کردن شماره سطرها (اختیاری)
        self.table_payments.setAlternatingRowColors(True)  # سطرها با رنگ متناوب برای خوانایی بهتر
        self.table_payments.setShowGrid(True)  # نمایش خطوط شبکه
        self.table_payments.setWordWrap(True)  # شکستن خطوط توضیحات بلند

        self.table_payments.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_payments.cellDoubleClicked.connect(self.handle_delete_payment)
        self.table_payments.cellClicked.connect(self.start_edit_payment)

        layout.addWidget(self.table_payments)

        # ---------- مجموع پرداخت فیلترشده ----------
        self.lbl_total_filtered = QLabel("مجموع پرداخت‌های نمایشی: 0 تومان")
        self.lbl_total_filtered.setStyleSheet("font-size:13px; color:green; margin-top:5px;")
        layout.addWidget(self.lbl_total_filtered)

        self.setLayout(layout)

        # ---------- داده اولیه ----------
        self.load_students()
        self.search_students()
        self.load_classes()
        self.load_filters()
        self.set_default_dates()
        self.load_payments()

    def clear_form(self):
        self.term_fee = int(get_setting("term_fee", self.term_fee))
        self.selected_student_id = None
        self.selected_student_teacher = None
        self.selected_class_id = None
        self.term_start = None
        self.term_end = None
        self.term_expired = True
        self.term_missing = False

        self.input_search_student.clear()
        self.list_students.clear()
        self.list_classes.clear()
        self.input_amount.setText(str(self.term_fee))

        self.input_min_amount.clear()
        self.input_max_amount.clear()
        self.input_keyword.clear()
        self.combo_filter_class.setCurrentIndex(0)
        self.input_search_all.clear()
        self.input_description.clear()

        self.combo_type.setCurrentIndex(0)

        self.lbl_total.setText("مجموع پرداخت شده: " + format_currency_with_unit(0))
        self.lbl_remaining.setText(f"باقی‌مانده شهریه (ترم جاری): {format_currency_with_unit(self.term_fee)}")

        # ریست و نمایش مجدد لیست هنرجویان
        self.load_students()
        self.search_students()
        self.set_default_dates()

        self.is_editing = False
        self.editing_payment_id = None
        self.btn_add_payment.setText("✅ ثبت پرداخت")

        self.set_payment_button_enabled(False)

        # ریست تاریخ انتخاب شده
        self.last_payment_date = QDate.currentDate()
        self.date_payment_picker.setDate(self.last_payment_date)

        # نمایش پرداخت‌ها (خالی چون چیزی انتخاب نشده)
        self.load_payments()

    def toggle_advanced(self):
        if self.adv_widget.isHidden():
            self.adv_widget.show()
            self.btn_advanced.setText("فیلتر پیشرفته 🔼")
        else:
            self.adv_widget.hide()
            self.btn_advanced.setText("فیلتر پیشرفته 🔽")

    def load_students(self):
        self.students = fetch_students_with_teachers()
        self.search_students()

    def search_students(self):
        query = self.input_search_student.text().lower().strip()
        self.list_students.clear()
        for row in self.students:
            if len(row) >= 4:
                sid, _, name, teacher = row[:4]
            else:
                continue
            if query in name.lower() or query in teacher.lower():
                item = QListWidgetItem(f"{name} (استاد: {teacher})")
                item.setData(Qt.UserRole, sid)
                self.list_students.addItem(item)

    def load_classes(self):
        self.classes = fetch_classes()

    def load_filters(self):
        self.combo_filter_class.clear()
        self.combo_filter_class.addItem("همه")
        for row in self.classes:
            if len(row) >= 2:
                cid, cname = row[0], row[1]

    def select_student(self, item):
        self.selected_student_id = item.data(Qt.UserRole)
        for row in self.students:
            sid, _, name, teacher = row[:4]
            if sid == self.selected_student_id:
                self.selected_student_teacher = teacher
                break

        # Load classes related to this teacher
        self.list_classes.clear()
        student_classes = fetch_registered_classes_for_student(self.selected_student_id)
        for cid, cname, tname, instr, day, start, end, room in student_classes:
            class_item = QListWidgetItem(f"{cname} ({day} {start}-{end}) - {tname}")
            class_item.setData(Qt.UserRole, cid)
            self.list_classes.addItem(class_item)

        # اگر فقط یک کلاس وجود داره، همون رو اتومات انتخاب کن
        if len(student_classes) == 1:
            item = self.list_classes.item(0)
            self.select_class(item)
        else:
            self.selected_class_id = None
            self.term_expired = True
            # فقط لیست پرداخت‌ها رو بارگذاری کن، نه اطلاعات مالی
            self.load_payments()
            self.lbl_total.setText("لطفاً یک کلاس را انتخاب کنید")
            self.lbl_remaining.setText("")
            self.set_payment_button_enabled(False)

    def select_class(self, item):
        self.selected_class_id = item.data(Qt.UserRole)
        self.update_term_status()
        self.update_financial_labels()
        self.load_payments()

    def load_payments(self):
        student_id = self.selected_student_id if self.selected_student_id else None
        class_id = self.selected_class_id if self.selected_class_id else None

        # تبدیل تاریخ‌ها به رشته میلادی
        date_from = self.date_from_picker.selected_shamsi
        date_to = self.date_to_picker.selected_shamsi

        raw = fetch_payments(
            student_id=student_id,
            class_id=class_id,
            date_from=date_from,
            date_to=date_to
        )

        filtered = []
        min_amt = self._to_int(self.input_min_amount.text())
        max_amt = self._to_int(self.input_max_amount.text())
        kw = self.input_keyword.text().lower().strip()
        sel_class = self.combo_filter_class.currentText()
        global_q = self.input_search_all.text().lower().strip()
        sel_ptype = self.combo_filter_ptype.currentText()

        for row in raw:
            if len(row) < 7:
                print(f"⚠️ ردیف ناقص: {row}")  # می‌تونی حذفش کنی بعداً
                continue
            pid, sname, cname, amount, pdate, desc, ptype = row
            try:
                j = jdatetime.date.fromisoformat(pdate)
                jdate = j.strftime("%Y/%m/%d")
            except:
                jdate = pdate  # fallback

            if min_amt is not None and amount < min_amt: continue
            if max_amt is not None and amount > max_amt: continue
            if kw and (not desc or kw not in desc.lower()): continue
            if sel_class != "همه" and cname != sel_class: continue
            if sel_ptype != "همه":
                if sel_ptype == "شهریه" and ptype != 'tuition':
                    continue
                if sel_ptype == "مازاد" and ptype != 'extra':
                    continue

            if global_q and not (
                    global_q in sname.lower() or
                    global_q in cname.lower() or
                    (desc and global_q in desc.lower())
            ):
                continue

            # نمایش فارسی نوع پرداخت، اما نوع اصلی را نگه می‌داریم برای رنگ‌بندی
            filtered.append((pid, sname, cname, amount, jdate, desc, ptype, "شهریه" if ptype == 'tuition' else "مازاد"))

        # مرتب‌سازی پرداخت‌ها در جدول به‌صورت نزولی بر اساس تاریخ
        def safe_jdate(dstr):
            try:
                return jdatetime.date.fromisoformat(dstr)
            except:
                return jdatetime.date(1400, 1, 1)

        filtered.sort(key=lambda x: safe_jdate(x[4]), reverse=True)

        total_displayed = sum([row[3] for row in filtered])
        self.lbl_total_filtered.setText(
            f"مجموع پرداخت‌های نمایشی: {format_currency_with_unit(total_displayed)} — تعداد: {len(filtered)} مورد"
        )

        # نمایش پرداخت‌ها در جدول
        self.table_payments.setRowCount(0)
        for row_data in filtered:
            row = self.table_payments.rowCount()
            self.table_payments.insertRow(row)

            payment_type = row_data[6]  # 'tuition' یا 'extra'

            for col, value in enumerate(row_data[:7]):  # ستون‌های ۰ تا ۶ (تا قبل از نوع پرداخت فارسی)
                item = QTableWidgetItem(str(value))
                if col == 0:
                    item.setData(Qt.UserRole, row_data[0])  # id پرداخت
                elif col == 1:
                    item.setData(Qt.UserRole, self.selected_student_id)
                elif col == 2:
                    item.setData(Qt.UserRole, self.selected_class_id)

                # رنگ‌بندی سلول بسته به نوع پرداخت
                if payment_type == "extra":
                    item.setBackground(QColor("#fff59d"))  # زرد ملایم
                elif payment_type == "tuition":
                    item.setBackground(QColor("#c8e6c9"))  # سبز ملایم

                self.table_payments.setItem(row, col, item)
                self.table_payments.setCellWidget(row, 6, None)  # پاک کردن احتمالی ویجت‌ها قبلی

            # ستون ۶ رو که فارسی‌سازی نوع پرداخت هست جداگانه ست می‌کنیم
            item = QTableWidgetItem(str(row_data[7]))
            if payment_type == "extra":
                item.setBackground(QColor("#fff59d"))
            elif payment_type == "tuition":
                item.setBackground(QColor("#c8e6c9"))
            self.table_payments.setItem(row, 6, item)

    def _to_int(self, text):
        try:
            return int(text)
        except:
            return None

    def update_term_status(self):
        """Determine if student has a term, and if it's expired (by session count)."""
        if self.selected_student_id and self.selected_class_id:
            term_id = get_term_id_by_student_and_class(self.selected_student_id, self.selected_class_id)
            if not term_id:
                self.term_missing = True
                self.term_expired = True
                return

            self.term_missing = False
            limit = int(get_setting("term_session_count", 12))
            done = count_attendance_for_term(term_id)  # ← استفاده مستقیم از term_id
            self.term_expired = (done >= limit)
        else:
            self.term_missing = False
            self.term_expired = True

    def update_financial_labels(self):
        """به‌روزرسانی اطلاعات مالی و جلسات برای ترم فعال."""
        self.lbl_total.setText("")
        self.lbl_remaining.setText("")
        self.set_payment_button_enabled(False)

        if not (self.selected_student_id and self.selected_class_id):
            return

        term_id = get_term_id_by_student_and_class(self.selected_student_id, self.selected_class_id)
        if not term_id:
            self.term_missing = True
            self.term_expired = True
            self.lbl_total.setText("هنرجو در این کلاس ثبت نشده است")
            return

        self.term_missing = False
        done = count_attendance_for_term(term_id)
        limit = int(get_setting("term_session_count", 12))
        self.term_expired = (done >= limit)

        if self.term_expired:
            self.lbl_total.setText("ترم تکمیل شده است")
            self.set_payment_button_enabled(False)
            return

        # ترم جاری فعال
        total = get_total_paid_for_term(term_id)
        rem_money = self.term_fee - total
        rem_sessions = limit - done
        self.lbl_total.setText(f"جلسات: {done} از {limit} — پرداخت: {format_currency_with_unit(total)}")
        self.lbl_total.setStyleSheet("font-size:13px; color: #555555;")

        # مانده شهریه رنگ‌بندی شود
        if rem_money == 0:
            color = "green"
        elif rem_money <= self.term_fee / 2:
            color = "#e6a800"  # زرد/نارنجی
        else:
            color = "red"

        self.lbl_remaining.setText(f"مانده شهریه: {format_currency_with_unit(rem_money)} — جلسات باقی: {rem_sessions}")
        self.lbl_remaining.setStyleSheet(f"font-size:13px; color:{color}; margin-bottom:10px;")

        self.set_payment_button_enabled(True)


    def add_payment(self):
        # اگر در حال ویرایش نیستیم، بررسی‌های ترم را انجام بده
        if not self.is_editing and (self.term_expired or not (self.selected_student_id and self.selected_class_id)):
            QMessageBox.warning(self, "خطا", "کاربر فاقد ترم جاری است یا انتخاب ناقص است.")
            return

        try:
            amount = int(self.input_amount.text())
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ باید عددی باشد.")
            return

        date_str = self.date_payment_picker.selected_shamsi
        desc = self.input_description.toPlainText().strip() or None
        ptype = 'tuition' if self.combo_type.currentText() == "شهریه" else 'extra'

        # فقط در حالت درج جدید بررسی و دریافت term_id انجام شود
        if not self.is_editing:
            term_id = get_term_id_by_student_and_class(self.selected_student_id, self.selected_class_id)
            if not term_id:
                QMessageBox.warning(self, "خطا", "ترم فعال یافت نشد.")
                return

            # فقط بررسی مانده در حالت شهریه و پرداخت جدید
            if ptype == 'tuition':
                total_paid = get_total_paid_for_term(term_id)
                remaining = self.term_fee - total_paid
                if amount > remaining:
                    QMessageBox.warning(
                        self, "خطا",
                        f"مبلغ واردشده از مانده شهریه بیشتر است ({format_currency_with_unit(remaining)} باقی‌مانده)."
                    )

            # درج پرداخت جدید
            insert_payment(
                self.selected_student_id,
                self.selected_class_id,
                term_id,
                amount,
                date_str,
                ptype,
                desc
            )
            QMessageBox.information(self, "موفق", "پرداخت با موفقیت ثبت شد.")
        else:
            # ویرایش پرداخت قبلی (نیاز به term_id ندارد)
            update_payment_by_id(
                payment_id=self.editing_payment_id,
                amount=amount,
                date=date_str,
                payment_type=ptype,
                description=desc
            )
            QMessageBox.information(self, "ویرایش شد", "پرداخت با موفقیت ویرایش شد.")
            del self.editing_payment_id
            self.editing_payment_id = None
            self.is_editing = False
            self.btn_add_payment.setText("✅ ثبت پرداخت")

        # ادامه پردازش
        self.last_payment_date = jdatetime.date.fromisoformat(date_str).togregorian()
        self.update_financial_labels()
        self.load_payments()
        self.clear_form()

    def handle_delete_payment(self, row, column):
        self.skip_next_edit = True

        # اگر در حالت ویرایش هستیم و همان ردیف را می‌خواهیم حذف کنیم:
        if self.is_editing:
            editing_row_payment_id = self.editing_payment_id
            clicked_payment_id = int(self.table_payments.item(row, 0).text())
            if editing_row_payment_id == clicked_payment_id:
                # ویرایش را لغو کن چون کاربر می‌خواهد حذف کند
                self.is_editing = False
                self.editing_payment_id = None
                self.btn_add_payment.setText("✅ ثبت پرداخت")

        payment_id_item = self.table_payments.item(row, 0)
        if not payment_id_item:
            return

        payment_id = int(payment_id_item.text())
        reply = QMessageBox.question(
            self, "حذف پرداخت", "آیا از حذف این پرداخت مطمئن هستید؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_payment(payment_id)
            self.load_payments()
            self.update_financial_labels()

        # فلگ را بعد از مدت کوتاهی پاک کن
        QTimer.singleShot(300, lambda: setattr(self, "skip_next_edit", False))


    def set_default_dates(self):
        # نمایش تمام پرداخت های هنرجو از این تاریخ
        # مقداردهی تاریخ شروع به 1380/01/01
        j_start = jdatetime.date(1380, 1, 1).togregorian()
        self.date_from_picker.setDate(QDate(j_start.year, j_start.month, j_start.day))

        # مقداردهی تاریخ پایان به امروز
        today = jdatetime.date.today().togregorian()
        self.date_to_picker.setDate(QDate(today.year, today.month, today.day))
        #todo : un# this line if ...
        # self.date_payment_picker.setDate(self.last_payment_date)

    def set_payment_button_enabled(self, enabled: bool):
        self.btn_add_payment.setEnabled(enabled)
        if enabled:
            self.btn_add_payment.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
        else:
            self.btn_add_payment.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                    padding: 6px;
                    font-weight: bold;
                }
            """)

    def start_edit_payment(self, row, column):
        if self.skip_next_edit:
            self.skip_next_edit = False  # فقط یک بار پرش کن
            return
        self.set_payment_button_enabled(True)

        # جلوگیری از شروع ویرایش هنگام کلیک روی سطر ناقص
        if any(self.table_payments.item(row, col) is None for col in range(7)):
            return

        payment_id_item = self.table_payments.item(row, 0)
        if not payment_id_item:
            return

        payment_id = int(payment_id_item.text())
        student_id_item = self.table_payments.item(row, 1)
        class_id_item = self.table_payments.item(row, 2)
        if student_id_item and class_id_item:
            self.selected_student_id = student_id_item.data(Qt.UserRole)
            self.selected_class_id = class_id_item.data(Qt.UserRole)

            # ست کردن هنرجو در لیست
            for i in range(self.list_students.count()):
                item = self.list_students.item(i)
                if item.data(1) == self.selected_student_id:
                    self.list_students.setCurrentItem(item)
                    break

            # بارگذاری کلاس‌ها و انتخاب کلاس
            self.list_classes.clear()
            student_classes = fetch_registered_classes_for_student(self.selected_student_id)
            for cid, cname, tname, instr, day, start, end, room in student_classes:
                class_item = QListWidgetItem(f"{cname} ({day} {start}-{end}) - {tname}")
                class_item.setData(Qt.UserRole, cid)
                self.list_classes.addItem(class_item)
                if cid == self.selected_class_id:
                    self.list_classes.setCurrentItem(class_item)

            self.update_term_status()
            self.update_financial_labels()
            self.set_payment_button_enabled(True)

        # اطلاعات سطر استخراج شود
        sname = self.table_payments.item(row, 1).text()
        cname = self.table_payments.item(row, 2).text()
        amount = self.table_payments.item(row, 3).text()
        date_str = self.table_payments.item(row, 4).text()
        description = self.table_payments.item(row, 5).text()
        payment_type_text = self.table_payments.item(row, 6).text()

        if self.is_editing:
            QMessageBox.warning(self, "ویرایش فعال", "لطفاً ابتدا ویرایش فعلی را کامل یا لغو کنید.")
            return

        # تبدیل به اطلاعات فرم
        self.input_amount.setText(amount)
        self.input_description.setText(description)
        self.combo_type.setCurrentText(payment_type_text)
        # تبدیل تاریخ به شمسی اگر لازم باشه
        try:
            jdate = jdatetime.datetime.strptime(date_str, "%Y/%m/%d").date()
            gdate = jdate.togregorian()
            self.date_payment_picker.setDate(QDate(gdate.year, gdate.month, gdate.day))
        except:
            pass

        self.is_editing = True
        self.editing_payment_id = payment_id
        self.btn_add_payment.setText("✏️ ویرایش پرداخت")

    def export_to_excel(self):
        row_count = self.table_payments.rowCount()
        col_count = self.table_payments.columnCount()

        if row_count == 0:
            QMessageBox.information(self, "خالی", "هیچ پرداختی برای خروجی وجود ندارد.")
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

        filename = f"پرداخت‌ها_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(self, "ذخیره فایل اکسل", filename, "Excel Files (*.xlsx)")

        if file_path:
            try:
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "موفق", "فایل با موفقیت ذخیره شد.")
            except Exception as e:
                QMessageBox.critical(self, "خطا", f"در ذخیره فایل مشکلی پیش آمد:\n{str(e)}")
