import sqlite3
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QTimeEdit, QMessageBox,QDialog
)
from PyQt5.QtCore import  QTime

from db_helper import (
    fetch_students_with_teachers, fetch_classes,
    add_session, fetch_sessions_by_class, delete_session,
    fetch_classes_for_student, has_weekly_time_conflict, update_session,
    get_day_and_time_for_class, is_class_slot_taken,
    insert_student_term_if_not_exists,
    delete_sessions_for_expired_terms,get_student_count_per_class,
get_unnotified_expired_terms,mark_terms_as_notified,get_term_id_by_student_and_class,
delete_term_if_no_payments
)
from shamsi_date_popup import ShamsiDatePopup
import jdatetime

class SessionManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت جلسات هنرجویان")
        self.setGeometry(350, 250, 500, 500)


        self.last_selected_date = jdatetime.date.today().strftime("%Y-%m-%d")
        self.selected_student_teacher_name = None
        self.students_data = []  # [(id, name, teacher)]
        self.selected_student_id = None
        self.selected_class_id = None

        self.selected_term_id = None

        self.is_editing = False
        self.selected_session_id = None

        layout = QVBoxLayout()

        # Search students
        layout.addWidget(QLabel("جستجوی هنرجو:"))
        self.input_search_student = QLineEdit()
        self.input_search_student.setPlaceholderText("نام هنرجو یا کد ملی هنرجو...")
        self.input_search_student.textChanged.connect(self.search_students)
        layout.addWidget(self.input_search_student)

        self.list_search_results = QListWidget()
        self.list_search_results.itemClicked.connect(self.select_student)
        layout.addWidget(self.list_search_results)

        self.input_search_class = QLineEdit()
        self.input_search_class.setPlaceholderText("جستجو بین کلاس‌های هنرجو...")
        self.input_search_class.textChanged.connect(self.filter_class_list)
        layout.addWidget(self.input_search_class)


        # Search class list (after student selected)
        layout.addWidget(QLabel("انتخاب کلاس مرتبط:"))
        self.list_classes = QListWidget()
        self.list_classes.itemClicked.connect(self.select_class)
        layout.addWidget(self.list_classes)

        # تاریخ شروع ترم
        self.date_btn = QPushButton("📅 انتخاب تاریخ شروع ترم")
        self.date_btn.clicked.connect(self.open_date_picker)
        layout.addWidget(self.date_btn)
        self.selected_shamsi_date = None
        self.selected_shamsi_date = self.last_selected_date
        self.date_btn.setText(f"📅 تاریخ شروع ترم: {self.selected_shamsi_date}")

        # ساعت جلسه
        layout.addWidget(QLabel("ساعت جلسه:"))
        self.time_session = QTimeEdit()
        self.time_session.setTime(QTime(12, 0))
        layout.addWidget(self.time_session)

        # دکمه افزودن جلسه
        self.btn_add_session = QPushButton("➕ افزودن جلسه")
        self.btn_add_session.clicked.connect(self.add_session_to_class)

        layout.addWidget(self.btn_add_session)

        # دکمه پاک‌سازی فرم
        self.btn_clear = QPushButton("🧹 پاک‌سازی فرم")
        self.btn_clear.clicked.connect(self.clear_form)
        layout.addWidget(self.btn_clear)

        # Sessions list
        layout.addWidget(QLabel("جلسات این کلاس (برای حذف دوبار کلیک کنید):"))
        self.list_sessions = QListWidget()
        self.list_sessions.itemDoubleClicked.connect(self.delete_session_from_class)
        self.list_sessions.itemClicked.connect(self.load_session_for_editing)
        layout.addWidget(self.list_sessions)

        self.setLayout(layout)
        self.load_students()
        self.search_students()  # نمایش اولیه

        self.check_and_notify_term_ends()
        delete_sessions_for_expired_terms()
        self.showMaximized()

        #بررسی میکنه که آیا لیستی از هنرجویان نمایش داده شده یا نه- اگر بله کلاس های مرتبط رو لود میکنه
        if self.list_search_results.count() > 0:
            first_item = self.list_search_results.item(0)
            self.list_search_results.setCurrentItem(first_item)
            self.select_student(first_item)

    def check_and_notify_term_ends(self):

        expired = get_unnotified_expired_terms()

        if expired:
            message = "هنرجویان زیر ترم‌شان به پایان رسیده است و از لیست کلاس حذف شدند:\n"
            for sid, cid, name, code, class_name, day, term_id in expired:
                message += f"\n• {name} | کد ملی: {code} | کلاس: {class_name} ({day})"

            # ⛳️ اول نمایش بده
            QMessageBox.information(self, "پایان ترم‌ها", message)

            # ✅ بعد علامت‌گذاری کن که پیام نمایش داده شده
            mark_terms_as_notified([(term_id, sid, cid) for sid, cid, _, _, _, _, term_id in expired])

    def clear_form(self):
        """Reset date/time and editing state without clearing student/class list"""
        self.input_search_student.clear()
        self.input_search_class.clear()
        self.selected_shamsi_date = self.last_selected_date
        self.date_btn.setText(f"📅 تاریخ شروع ترم: {self.selected_shamsi_date}")
        # ساعت کلاس را حفظ کن، فقط در صورت نیاز به مقداردهی مجدد مقدار بده
        self.is_editing = False
        self.btn_add_session.setText("➕ افزودن جلسه")
        self.selected_session_id = None
        # نتایج جستجو را مجدد فیلتر کن تا لیست به‌روزرسانی شود
        self.filter_class_list()
        self.search_students()
        self.time_session.setTime(QTime(12, 0))

    def load_students(self):
        self.students_data = fetch_students_with_teachers()
        self.search_students()

    def load_student_classes(self):
        self.list_classes.clear()

        if not self.selected_student_id:
            return

        classes = fetch_classes_for_student(self.selected_student_id)
        student_counts = get_student_count_per_class()

        for cid, cname, teacher_name, day in classes:
            count = student_counts.get(cid, 0)
            item = QListWidgetItem(f"{cname} (استاد: {teacher_name}، روز: {day}) - {count} هنرجو جلسه دارد")
            item.setData(1, cid)
            self.list_classes.addItem(item)

    def search_students(self):
        query = self.input_search_student.text().lower().strip()
        self.list_search_results.clear()
        for sid, national_code, name, teacher in self.students_data:
            if query in name.lower() or query in national_code.lower():
                item = QListWidgetItem(f"{name} - کدملی: {national_code}")
                item.setData(1, sid)  # ذخیره student_id صحیح
                self.list_search_results.addItem(item)

    def select_student(self, item):
        self.selected_student_id = item.data(1)

        # Save teacher name for this student
        for sid, national_code, name, teacher in self.students_data:
            if sid == self.selected_student_id:
                self.selected_student_teacher_name = teacher
                break
        self.load_student_classes()
        self.filter_class_list()

    def select_class(self, item):
        self.selected_class_id = item.data(1)
        # تنظیم خودکار ساعت جلسه بر اساس ساعت شروع کلاس
        for cls in fetch_classes():
            if cls[0] == self.selected_class_id:
                start_time = cls[5]
                if start_time:
                    self.time_session.setTime(QTime.fromString(start_time, "HH:mm"))
                break

        self.load_sessions()  # Load sessions for selected class

    def add_session_to_class(self):
        if not self.selected_class_id or not self.selected_student_id:
            QMessageBox.warning(self, "خطا", "لطفاً هنرجو و کلاس را انتخاب کنید.")
            return

        # استفاده از تاریخ شمسی انتخاب‌شده
        if not self.selected_shamsi_date:
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ جلسه (شمسی) را انتخاب کنید.")
            return

        date = self.selected_shamsi_date
        time = self.time_session.time().toString("HH:mm")

        class_day, _ = get_day_and_time_for_class(self.selected_class_id)
        session_time = self.time_session.time().toString("HH:mm")

        # حالت ویرایش
        if self.is_editing:
            self.update_session()
            return

        # بررسی اینکه آیا زمان جلسه خالی است یا خیر
        if is_class_slot_taken(self.selected_class_id, date, time):
            QMessageBox.warning(self, "تداخل کلاس", "در این روز و ساعت، کلاس برای هنرجوی دیگری رزرو شده است.")
            return

        if has_weekly_time_conflict(self.selected_student_id, class_day, session_time):
            QMessageBox.warning(self, "تداخل هفتگی", "هنرجو در این روز و ساعت کلاس دیگری دارد.")
            return

        try:
            add_session(self.selected_class_id, self.selected_student_id, date, time)
            QMessageBox.information(self, "موفق", f"جلسه برای هنرجو با موفقیت در تاریخ {date} و ساعت {time} ثبت شد.")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "جلسه تکراری", "این جلسه قبلاً ثبت شده است یا تداخل زمانی دارد.")
            return

        self.load_sessions()
        self.last_selected_date = self.selected_shamsi_date  # این خط عملاً بی‌تأثیره چون بالاتر هم هست

    def load_sessions(self):
        self.list_sessions.clear()
        if not self.selected_class_id:
            return
        for row in fetch_sessions_by_class(self.selected_class_id):
            s_item = QListWidgetItem(f"{row[1]} - {row[2]} ساعت {row[3]}")
            s_item.setData(1, row[0])
            self.list_sessions.addItem(s_item)

    def delete_session_from_class(self, item):
        session_id = item.data(1)

        # قبل از هر چیز بپرس آیا می‌خواهی حذف شود
        reply = QMessageBox.question(self, "حذف جلسه", "آیا این جلسه حذف شود؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # قبل از حذف جلسه، بررسی کن که ترم پرداختی دارد یا نه
        term_id = get_term_id_by_student_and_class(self.selected_student_id, self.selected_class_id)
        has_payment = not delete_term_if_no_payments(self.selected_student_id, self.selected_class_id, term_id)

        if has_payment:
            QMessageBox.warning(self, "حذف ممکن نیست",
                                "برای ترم این هنرجو پرداخت ثبت شده است. لطفاً ابتدا پرداخت‌ها را حذف کنید، سپس اقدام به حذف جلسه نمایید.")
            return

        # اگر پرداختی ندارد، حذف جلسه و پیام موفقیت
        delete_session(session_id)
        self.load_sessions()
        QMessageBox.information(self, "موفق", "جلسه و ترم مرتبط با موفقیت حذف شدند.")
        self.clear_form()

    def filter_class_list(self):
        query = self.input_search_class.text().lower().strip()
        for i in range(self.list_classes.count()):
            item = self.list_classes.item(i)
            item.setHidden(query not in item.text().lower())

    def load_session_for_editing(self, item):
        self.selected_session_id = item.data(1)
        self.is_editing = True
        self.btn_add_session.setText("💾 ذخیره تغییرات")

        # گرفتن اطلاعات جلسه انتخاب‌شده
        sessions = fetch_sessions_by_class(self.selected_class_id)
        for s_id, student_name, date_str, time_str, _ in sessions:
            if s_id == self.selected_session_id:
                # ذخیره تاریخ شمسی برای استفاده در ذخیره‌سازی
                self.selected_shamsi_date = date_str
                self.date_btn.setText(f"📅 {date_str}")

                # تنظیم ساعت جلسه
                self.time_session.setTime(QTime.fromString(time_str, "HH:mm"))
                break

    def update_session(self):
        if not self.selected_shamsi_date:
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ جلسه (شمسی) را انتخاب کنید.")
            return

        date = self.selected_shamsi_date
        time = self.time_session.time().toString("HH:mm")

        class_day, _ = get_day_and_time_for_class(self.selected_class_id)
        session_time = self.time_session.time().toString("HH:mm")

        # بررسی تداخل هفتگی
        if has_weekly_time_conflict(self.selected_student_id, class_day, session_time,
                                    exclude_session_id=self.selected_session_id):
            QMessageBox.warning(self, "تداخل هفتگی", "هنرجو در این روز و ساعت کلاس دیگری دارد.")
            return

        # بررسی تداخل زمان با هنرجوی دیگر
        if is_class_slot_taken(self.selected_class_id, date, time) and not self.is_editing:
            QMessageBox.warning(self, "تداخل کلاس", "در این روز و ساعت، کلاس برای هنرجوی دیگری رزرو شده است.")
            return

        # بررسی انتخاب کلاس و هنرجو
        if not self.selected_class_id or not self.selected_student_id:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا هنرجو و کلاس را انتخاب کنید.")
            return

        try:
            update_session(
                self.selected_session_id,
                self.selected_class_id,
                self.selected_student_id,
                date,
                time
            )
            QMessageBox.information(self, "موفق", "جلسه با موفقیت ویرایش شد.")

            # اگر هنرجو هنوز ترمی نداشته، بساز
            insert_student_term_if_not_exists(self.selected_student_id, self.selected_class_id, date)

        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "خطا", "امکان ویرایش به دلیل تداخل یا جلسه تکراری وجود ندارد.")
            return

        self.is_editing = False
        self.selected_session_id = None
        self.selected_shamsi_date = None
        self.date_btn.setText("📅 انتخاب تاریخ جلسه (شمسی)")
        self.btn_add_session.setText("➕ افزودن جلسه")
        self.load_sessions()
        self.clear_form()
        self.load_student_classes()

    def open_date_picker(self):
        dlg = ShamsiDatePopup(initial_date=self.selected_shamsi_date)
        if dlg.exec_() == QDialog.Accepted:
            self.selected_shamsi_date = dlg.get_selected_date()
            self.last_selected_date = self.selected_shamsi_date
            self.date_btn.setText(f"📅 {self.selected_shamsi_date}")
