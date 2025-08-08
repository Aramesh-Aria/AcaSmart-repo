from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QFormLayout, QTextEdit, QComboBox, QMessageBox
)
from PySide6.QtCore import QDate, Qt
from db_helper import (
    fetch_students_with_teachers, fetch_classes,
    insert_payment, get_total_paid_for_term, get_setting,
    get_term_id_by_student_and_class,count_attendance_for_term,fetch_registered_classes_for_student,
    update_payment_by_id, get_terms_for_payment_management
)
from shamsi_date_popup import ShamsiDatePopup
from shamsi_date_picker import ShamsiDatePicker
import jdatetime
from utils import format_currency_with_unit ,get_currency_unit,format_currency
from payment_report_window import PaymentReportWindow

class PaymentManager(QWidget):
    
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
        self.is_editing = False
        self.editing_payment_id = None
        self.selected_student_id = None
        self.selected_student_teacher = None
        self.selected_class_id = None
        self.selected_term_id = None
        self.students = []
        self.classes = []

        layout = QVBoxLayout()

        # ---------- فیلتر اولیه ----------
        layout.addWidget(QLabel("جستجوی هنرجو:"))
        self.input_search_student = QLineEdit()
        self.input_search_student.setPlaceholderText("نام هنرجو یا استاد...")
        self.input_search_student.textChanged.connect(self.search_students)
        layout.addWidget(self.input_search_student)

        self.list_students = QListWidget()
        self.list_students.itemClicked.connect(self.select_student)
        layout.addWidget(self.list_students)

        layout.addWidget(QLabel("انتخاب کلاس مرتبط:"))
        self.list_classes = QListWidget()
        self.list_classes.itemClicked.connect(self.select_class)
        layout.addWidget(self.list_classes)

        # ---------- انتخاب ترم ----------
        layout.addWidget(QLabel("انتخاب ترم:"))
        self.combo_terms = QComboBox()
        self.combo_terms.currentIndexChanged.connect(self.select_term)
        layout.addWidget(self.combo_terms)

        # ---------- فرم پرداخت ----------
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)

        self.input_amount = QLineEdit(str(self.term_fee))
        form_layout.addRow("💰 مبلغ پرداختی:", self.input_amount)

        self.date_payment_picker = ShamsiDatePicker()
        self.date_payment_picker.setDate(self.last_payment_date)  # استفاده از مقدار ذخیره‌شده
        form_layout.addRow("📅 تاریخ پرداخت:", self.date_payment_picker)

        self.combo_type = QComboBox()
        self.combo_type.addItems(["شهریه", "مازاد"])
        self.combo_type.currentIndexChanged.connect(self.update_financial_labels)
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

        # دکمه مشاهده گزارش
        self.btn_show_report = QPushButton("📊 مشاهده گزارش پرداخت‌ها")
        self.btn_show_report.clicked.connect(self.open_report_window)
        layout.addWidget(self.btn_show_report)


        self.setLayout(layout)

        # ---------- داده اولیه ----------
        self.load_students()
        self.search_students()
        self.load_classes()

    def clear_form(self):
        self.term_fee = int(get_setting("term_fee", self.term_fee))
        self.selected_student_id = None
        self.selected_student_teacher = None
        self.selected_class_id = None
        self.selected_term_id = None
        self.term_start = None
        self.term_end = None
        self.term_expired = True
        self.term_missing = False

        self.input_search_student.clear()
        self.list_students.clear()
        self.list_classes.clear()
        self.combo_terms.clear()
        self.input_amount.setText(str(self.term_fee))

        self.input_description.clear()

        self.combo_type.setCurrentIndex(0)

        self.lbl_total.setText("مجموع پرداخت شده: " + format_currency_with_unit(0))
        self.lbl_remaining.setText(f"باقی‌مانده شهریه (ترم جاری): {format_currency_with_unit(self.term_fee)}")

        # ریست و نمایش مجدد لیست هنرجویان
        self.load_students()
        self.search_students()
        self.btn_add_payment.setText("✅ ثبت پرداخت")

        self.set_payment_button_enabled(False)

        # ریست تاریخ انتخاب شده
        self.last_payment_date = QDate.currentDate()
        self.date_payment_picker.setDate(self.last_payment_date)


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
            self.lbl_total.setText("لطفاً یک کلاس را انتخاب کنید")
            self.lbl_remaining.setText("")
            self.set_payment_button_enabled(False)

    def select_class(self, item):
        self.selected_class_id = item.data(Qt.UserRole)
        self.load_terms()
        self.update_term_status()
        self.update_financial_labels()

    def load_terms(self):
        """بارگذاری تمام ترم‌های هنرجو در کلاس انتخاب‌شده"""
        self.combo_terms.clear()
        self.selected_term_id = None
        
        if not (self.selected_student_id and self.selected_class_id):
            return
            
        terms = get_terms_for_payment_management(self.selected_student_id, self.selected_class_id)
        
        if not terms:
            self.combo_terms.addItem("هیچ ترمی یافت نشد", None)
            return
            
        for term in terms:
            term_id = term['term_id']
            start_date = term['start_date']
            end_date = term['end_date']
            status = term['status']
            term_status = term['term_status']
            total_paid = term['total_paid']
            debt = term['debt']
            
            # نمایش اطلاعات ترم
            display_text = f"ترم {start_date}"
            if end_date:
                display_text += f" تا {end_date}"
            display_text += f" - {term_status}"
            
            # نمایش وضعیت پرداخت
            if debt == 0:
                payment_status = "تسویه شده"
            elif debt > 0:
                payment_status = f"بدهکار: {format_currency_with_unit(debt)}"
            else:
                payment_status = "خطا"
                
            display_text += f" - {payment_status}"
            if total_paid > 0:
                display_text += f" (پرداخت: {format_currency_with_unit(total_paid)})"
                
            self.combo_terms.addItem(display_text, term_id)
        
        # انتخاب اولین ترم به عنوان پیش‌فرض
        if self.combo_terms.count() > 0:
            self.combo_terms.setCurrentIndex(0)

    def select_term(self, index):
        """انتخاب ترم و به‌روزرسانی اطلاعات مالی"""
        if index >= 0:
            self.selected_term_id = self.combo_terms.itemData(index)
        else:
            self.selected_term_id = None
        
        self.update_term_status()
        self.update_financial_labels()

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
        """به‌روزرسانی اطلاعات مالی و جلسات برای ترم انتخاب‌شده."""
        self.lbl_total.setText("")
        self.lbl_remaining.setText("")
        self.set_payment_button_enabled(False)

        if not (self.selected_student_id and self.selected_class_id):
            return

        if not self.selected_term_id:
            self.term_missing = True
            self.term_expired = True
            self.lbl_total.setText("لطفاً یک ترم را انتخاب کنید")
            return

        self.term_missing = False
        done = count_attendance_for_term(self.selected_term_id)
        limit = int(get_setting("term_session_count", 12))
        self.term_expired = (done >= limit)

        # اطلاعات مالی ترم انتخاب‌شده
        total = get_total_paid_for_term(self.selected_term_id)
        rem_money = self.term_fee - total
        rem_sessions = limit - done
        
        # تعیین وضعیت ترم
        term_status = "تکمیل شده" if self.term_expired else "فعال"
        
        self.lbl_total.setText(f"ترم {term_status} — جلسات: {done} از {limit} — پرداخت: {format_currency_with_unit(total)}")
        self.lbl_total.setStyleSheet("font-size:13px; color: #555555;")

        # مانده شهریه رنگ‌بندی شود
        if rem_money == 0:
            color = "rgb(0, 128, 0)" # سبز پررنگ
        elif rem_money <= self.term_fee / 2:
            color = "rgb(255, 140, 0)"  # زرد/نارنجی
        else:
            color = "rgb(178, 34, 34)"   # قرمز پررنگ

        self.lbl_remaining.setText(f"مانده شهریه: {format_currency_with_unit(rem_money)} — جلسات باقی: {rem_sessions}")
        self.lbl_remaining.setStyleSheet(f"font-size:13px; color:{color}; margin-bottom:10px;")

        # نوع پرداخت انتخاب‌شده رو بگیر
        ptype = self.combo_type.currentText()
        if ptype == "شهریه":
            # فقط وقتی شهریه بدهکار هست دکمه فعال شه
            can_pay = rem_money > 0
        else:
            # برای پرداخت مازاد همیشه فعال باشه
            can_pay = True
        self.set_payment_button_enabled(can_pay)


    def add_payment(self):

        ptype = 'tuition' if self.combo_type.currentText() == "شهریه" else 'extra'

        try:
            amount = int(self.input_amount.text())
        except ValueError:
            QMessageBox.warning(self, "خطا", "مبلغ باید عددی باشد.")
            return

        date_str = self.date_payment_picker.selected_shamsi
        desc = self.input_description.toPlainText().strip() or None

        # فقط در حالت درج جدید بررسی و دریافت term_id انجام شود
        if not self.is_editing:
            if not self.selected_term_id:
                QMessageBox.warning(self, "خطا", "لطفاً یک ترم را انتخاب کنید.")
                return

            # بررسی مانده در حالت شهریه و پرداخت جدید
            if ptype == 'tuition':
                total_paid = get_total_paid_for_term(self.selected_term_id)
                remaining = self.term_fee - total_paid
                
                if remaining <= 0:
                    QMessageBox.warning(self, "خطا", "این ترم قبلاً به طور کامل پرداخت شده است.")
                    return
                    
                if amount > remaining:
                    remaining_str = format_currency_with_unit(remaining)
                    QMessageBox.warning(
                        self, "خطا",
                        f"مبلغ واردشده از مانده شهریه بیشتر است ({(remaining_str)} باقی‌مانده)."
                    )
                    return

            # درج پرداخت جدید
            insert_payment(
                self.selected_student_id,
                self.selected_class_id,
                self.selected_term_id,
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
            self.is_editing = False
            self.btn_add_payment.setText("✅ ثبت پرداخت")

        # ادامه پردازش
        try:

            self.last_payment_date = jdatetime.date.fromisoformat(date_str).togregorian()
        except Exception as e:
            QMessageBox.warning(self, "خطا", "مشکلی در تبدیل تاریخ پیش آمده است.")
            print(f"error in pay_manager: {e}")
        self.update_financial_labels()
        self.clear_form()
        # اگر پنجره گزارش باز است، داده‌ها را تازه‌سازی کن
        if hasattr(self, "report_window") and self.report_window.isVisible():
            self.report_window.load_payments()

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

    def open_report_window(self):
        self.report_window = PaymentReportWindow(
            student_id=self.selected_student_id,
            class_id=self.selected_class_id
        )
        self.report_window.payment_changed.connect(self.update_financial_labels)  # وقتی حذف شد آپدیت کن
        self.report_window.show()
