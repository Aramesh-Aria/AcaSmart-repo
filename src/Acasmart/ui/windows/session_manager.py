from Acasmart.data.repos.classes_repo import get_day_and_time_for_class
from Acasmart.data.repos.notifications_repo import get_unnotified_expired_terms, mark_terms_as_notified
from Acasmart.data.repos.payments_repo import delete_term_if_no_payments
from Acasmart.data.repos.profiles_repo import list_pricing_profiles
from Acasmart.data.repos.sessions_repo import add_session, delete_session, delete_sessions_for_expired_terms, delete_sessions_for_term, fetch_sessions_by_class, get_session_by_id, get_session_count_per_class, get_session_count_per_student, has_teacher_weekly_time_conflict, has_weekly_time_conflict, is_class_slot_taken, update_session
from Acasmart.data.repos.settings_repo import get_setting
from Acasmart.data.repos.students_repo import fetch_classes_for_student, fetch_students_with_teachers
from Acasmart.data.repos.terms_repo import get_finished_terms_with_future_sessions, get_last_term_end_date, insert_student_term_if_not_exists
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QTimeEdit, QMessageBox, QDialog,
    QDialogButtonBox, QHBoxLayout, QComboBox, QRadioButton, QSpinBox
)
from PySide6.QtCore import QTime, Qt
from Acasmart.ui.widgets.shamsi_date_popup import ShamsiDatePopup
import jdatetime
import sqlite3
from Acasmart.core.fa_collation import sort_records_fa, contains_fa,nd,fa_digits
from Acasmart.core.utils import currency_label, format_currency_with_unit, parse_user_amount_to_toman
from Acasmart.core.fa_collation import fa_digits

class TermConfigDialog(QDialog):
    """
    انتخاب پروفایل/ترم سفارشی برای ساخت ترم همراه با جلسهٔ اول.
    خروجی: dict با کلیدهای sessions_limit, tuition_fee, currency_unit, profile_id (همه Optional)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات ترم")

        # حالت‌ها
        self.rb_profile = QRadioButton("استفاده از پروفایل شهریه")
        self.rb_custom  = QRadioButton("سفارشی")
        self.rb_profile.setChecked(True)
        self.ui_unit = currency_label()  # "تومان" یا "ریال"

        # پروفایل‌ها
        self.profile_combo = QComboBox()
        self.profiles = list_pricing_profiles()  # [(id, name, sessions_limit, tuition_fee, currency_unit, is_default)]
        for pid, name, sl, fee_toman, unit, is_def in self.profiles:
            label = f"{name} — {sl} جلسه، {format_currency_with_unit(fee_toman)}"
            self.profile_combo.addItem(label, pid)
            if is_def:
                self.profile_combo.setCurrentIndex(self.profile_combo.count() - 1)

        # بعد از حلقهٔ افزودن آیتم‌های پروفایل به کمبو:
        if not self.profiles:
            self.rb_profile.setEnabled(False)
            self.profile_combo.setEnabled(False)
            self.rb_custom.setChecked(True)

        # ورودی سفارشی
        self.spin_sessions = QSpinBox()
        self.spin_sessions.setRange(1, 100)
        self.spin_sessions.setValue(int(get_setting("term_session_count", 12)))

        self.spin_fee = QSpinBox()
        self.spin_fee.setRange(0, 1_000_000_000)
        self.spin_fee.setSingleStep(10000)

        # مقدار اولیه‌ی «تومان خام» از تنظیمات:
        base_fee_toman = int(get_setting("term_fee", get_setting("term_tuition", 6000000)))
        # برای نمایش: اگر UI روی ریال است، ×۱۰
        display_fee = base_fee_toman * 10 if self.ui_unit == "ریال" else base_fee_toman
        self.spin_fee.setValue(int(display_fee))

        # نمایش واحد
        self.currency_unit = get_setting("currency_unit", "toman")
        self.lbl_unit = QLabel(f"واحد: {self.ui_unit}")  # ← واحد نمایش فعلی

        # چیدمان
        lay = QVBoxLayout(self)
        lay.addWidget(self.rb_profile)
        lay.addWidget(self.profile_combo)
        lay.addSpacing(8)
        lay.addWidget(self.rb_custom)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("سقف جلسات:"))
        row1.addWidget(self.spin_sessions)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel(f"شهریه ترم (به {self.ui_unit}):"))
        row2.addWidget(self.spin_fee)
        lay.addLayout(row2)

        lay.addWidget(self.lbl_unit)

        # دکمه‌ها
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        # فعال/غیرفعال‌سازی ورودی‌های سفارشی
        def sync_enabled():
            custom = self.rb_custom.isChecked()
            self.spin_sessions.setEnabled(custom)
            self.spin_fee.setEnabled(custom)
        self.rb_profile.toggled.connect(sync_enabled)
        self.rb_custom.toggled.connect(sync_enabled)
        sync_enabled()

    def get_config(self):
        if self.rb_custom.isChecked():
            # مقدار نمایش‌داده‌شده (ممکن است ریال باشد) → تبدیل به «تومان خام»
            fee_toman = parse_user_amount_to_toman(str(self.spin_fee.value()))
            return {
                "sessions_limit": int(self.spin_sessions.value()),
                "tuition_fee":   int(fee_toman),   # همیشه تومان
                "currency_unit": self.currency_unit,
                "profile_id":    None,
            }
        else:
            pid = self.profile_combo.currentData()
            row = next((p for p in self.profiles if p[0] == pid), None)
            if row:
                _, _, sl, fee_toman, unit, _ = row
                return {
                    "sessions_limit": int(sl),
                    "tuition_fee":   int(fee_toman),                 # تومان خام از پروفایل
                    "currency_unit": unit or self.currency_unit,
                    "profile_id":    pid,
                }
            return {"sessions_limit": None, "tuition_fee": None, "currency_unit": None, "profile_id": None}


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

        self.last_selected_time = None
        self.last_time_per_class = {}  # کلاس به ساعت آخر ثبت‌شده

        self.session_counts_by_student = {}  # {student_id: count}
        self.refresh_session_counts()        # ← اولین بارگیری

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
        self.time_session.timeChanged.connect(self.on_time_changed)
        layout.addWidget(self.time_session)

        # دکمه افزودن جلسه
        self.btn_add_session = QPushButton("➕ افزودن جلسه")
        self.btn_add_session.clicked.connect(self.add_session_to_class)

        layout.addWidget(self.btn_add_session)

        # دکمه پاک‌سازی فرم
        self.btn_clear = QPushButton("🧹 پاک‌سازی فرم")
        self.btn_clear.clicked.connect(self.clear_form)
        layout.addWidget(self.btn_clear)

        # دکمه پاکسازی ترم پایان یافته
        self.btn_notify_expired = QPushButton("📣 نمایش ترم‌های پایان‌یافته (بدون حذف)")
        self.btn_notify_expired.clicked.connect(self.check_and_notify_term_ends)
        layout.addWidget(self.btn_notify_expired)

        self.btn_cleanup = QPushButton("🗑️ پاکسازی جلسات آیندهٔ ترم‌های پایان‌یافته")
        self.btn_cleanup.clicked.connect(self.manual_cleanup_expired_sessions)
        layout.addWidget(self.btn_cleanup)

        # Sessions list
        layout.addWidget(QLabel("جلسات این کلاس (برای حذف دوبار کلیک کنید):"))
        self.list_sessions = QListWidget()
        self.list_sessions.setSortingEnabled(False) # Qt خودش با متن سورت نکند
        self.list_sessions.itemDoubleClicked.connect(self.delete_session_from_class)
        self.list_sessions.itemClicked.connect(self.load_session_for_editing)
        layout.addWidget(self.list_sessions)

        self.setLayout(layout)
        self.load_students()
        self.search_students()  # نمایش اولیه

        self.check_and_notify_term_ends()
        # delete_sessions_for_expired_terms()
        self.showMaximized()

        #بررسی میکنه که آیا لیستی از هنرجویان نمایش داده شده یا نه- اگر بله کلاس های مرتبط رو لود میکنه
        if self.list_search_results.count() > 0:
            first_item = self.list_search_results.item(0)
            self.list_search_results.setCurrentItem(first_item)
            self.select_student(first_item)

    def refresh_session_counts(self):
        try:
            self.session_counts_by_student = get_session_count_per_student() or {}
        except Exception:
            self.session_counts_by_student = {}

    def check_and_notify_term_ends(self):
        expired = get_unnotified_expired_terms()
        if not expired:
            return

        message = "هنرجویان زیر ترم‌شان به پایان رسیده است :\n"
        to_mark = []

        for student_id, class_id, student_name, national_code, class_name, day, term_id, session_date, session_time in expired:
            message += f"\n• {student_name} | کدملی: {national_code} | {class_name} ({day}) — {session_date} ساعت {session_time}"
            to_mark.append((term_id, student_id, class_id, session_date, session_time))

        # ⛳️ اول نمایش بده
        QMessageBox.information(self, "پایان ترم‌ها", message)

        # ✅ بعد علامت‌گذاری کن که پیام نمایش داده شده
        # mark_terms_as_notified(to_mark)

        # #  حذف جلسات مربوط به این ترم
        # for term_id, *_ in to_mark:
        #     delete_sessions_for_term(term_id)
    
    def clear_form(self):
        """Reset date/time and editing state without clearing student/class list"""
        self.input_search_student.clear()
        self.input_search_class.clear()
        self.selected_shamsi_date = self.last_selected_date
        self.date_btn.setText(f"📅 تاریخ شروع ترم: {self.selected_shamsi_date}")
        self.is_editing = False
        self.btn_add_session.setText("➕ افزودن جلسه")
        self.selected_session_id = None
        self.filter_class_list()
        self.search_students()
        
        # تنظیم ساعت بر اساس کلاس انتخاب‌شده
        if self.selected_class_id:
            class_day, class_time = get_day_and_time_for_class(self.selected_class_id)
            if class_time:
                try:
                    self.time_session.setTime(QTime.fromString(class_time, "HH:mm"))
                except:
                    self.time_session.setTime(QTime(12, 0))
            else:
                self.time_session.setTime(QTime(12, 0))
        else:
            self.time_session.setTime(QTime(12, 0))
        
        self.last_selected_time = None

    def on_time_changed(self):
        """Remember the time when user changes it"""
        if self.selected_class_id:
            self.last_selected_time = self.time_session.time()
            self.last_time_per_class[self.selected_class_id] = self.last_selected_time
            # Reset the global last_selected_time so it doesn't override class start times
            self.last_selected_time = None

    def load_students(self):
        rows = fetch_students_with_teachers()  # [(sid, national_code, name, teacher), ...]
        # سورت بر اساس نام فارسی (index=2) و در صورت تساوی بر اساس کدملی (index=1)
        self.students_data = sort_records_fa(rows, name_index=2, tiebreak_index=1)
        self.search_students()

    def load_student_classes(self):
        self.list_classes.clear()

        if not self.selected_student_id:
            return

        classes = fetch_classes_for_student(self.selected_student_id)
        session_counts = get_session_count_per_class()

        # ترتیب روزهای هفته
        week_order = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
        classes.sort(key=lambda x: week_order.index(x[3]) if x[3] in week_order else 7)

        # 🎨 رنگ‌ها برای هر روز هفته (بدون سبز و قرمز)
        day_colors = {
            "شنبه": "#ADD8E6",      # آبی روشن
            "یکشنبه": "#FFD580",    # نارنجی روشن
            "دوشنبه": "#E6E6FA",    # بنفش روشن
            "سه‌شنبه": "#FFFACD",   # لیمویی
            "چهارشنبه": "#FFC0CB",  # صورتی روشن
            "پنجشنبه": "#D3D3D3",   # خاکستری روشن
            "جمعه": "#F5DEB3",      # بژ روشن
        }

        for cid, cname, teacher_name, day in classes:
            count = session_counts.get(cid, 0)

            # ساخت QLabel با رنگ پس‌زمینه مخصوص روز
            label = QLabel(f"<b>{cname}</b> - <span style='color:#444'>استاد: {teacher_name}</span><br>"
                        f"<span style='font-size:11px; color:#555'>روز: {day} | {count} جلسه ثبت شده</span>")
            label.setTextFormat(Qt.RichText)
            label.setStyleSheet(f"""
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 5px;
                background-color: {day_colors.get(day, "#FFFFFF")};
            """)
            label.setAttribute(Qt.WA_TransparentForMouseEvents)

            item = QListWidgetItem()
            item.setSizeHint(label.sizeHint())
            item.setData(Qt.UserRole, cid)

            self.list_classes.addItem(item)
            self.list_classes.setItemWidget(item, label)

    def search_students(self):
        raw = self.input_search_student.text().strip()
        q_name = raw           # contains_fa خودش نرمال‌سازی فارسی را انجام می‌دهد
        q_code = nd(raw)       # ← ارقام را یکسان کن

        self.list_search_results.clear()

        # فیلتر
        filtered = []
        for sid, national_code, name, teacher in self.students_data:
            if contains_fa(name, q_name) or (q_code and q_code in nd(national_code)):
                filtered.append((sid, national_code, name, teacher))

        # سورت نتایج بر اساس نام فارسی
        filtered = sort_records_fa(filtered, name_index=2, tiebreak_index=1)

        # نمایش
        for sid, national_code, name, teacher in filtered:
            count = self.session_counts_by_student.get(sid, 0)
            count_fa = fa_digits(count)
            item = QListWidgetItem(f"{name} - کد ملی: {national_code} ( {count_fa} جلسه ثبت شده )")

            item.setData(Qt.UserRole, sid)
            self.list_search_results.addItem(item)
            
    def select_student(self, item):
        self.selected_student_id = item.data(Qt.UserRole)

        # ذخیره نام استاد
        for sid, national_code, name, teacher in self.students_data:
            if sid == self.selected_student_id:
                self.selected_student_teacher_name = teacher
                break

        self.load_student_classes()
        self.filter_class_list()

        # ✅ اگر کلاس‌ها لود شدند، اولین کلاس رو انتخاب و ساعت رو آپدیت کن
        if self.list_classes.count() > 0:
            first_class_item = self.list_classes.item(0)
            self.list_classes.setCurrentItem(first_class_item)
            # Reset last_selected_time when switching students to ensure class start time is loaded
            self.last_selected_time = None
            self.select_class(first_class_item)

    def select_class(self, item):
        self.selected_class_id = item.data(Qt.UserRole)
        
        # گرفتن آخرین ساعت ثبت‌شده برای این کلاس
        last_time = self.last_time_per_class.get(self.selected_class_id)

        # اول سعی کن ساعت شروع کلاس را لود کن
        class_day, class_start_time = get_day_and_time_for_class(self.selected_class_id)
        if class_start_time:
            try:
                self.time_session.setTime(QTime.fromString(class_start_time, "HH:mm"))
                # اگر این کلاس قبلاً ساعت دستی داشت، آن را حفظ کن
                if last_time:
                    self.last_time_per_class[self.selected_class_id] = self.time_session.time()
            except:
                # اگر فرمت زمان مشکل داشت، ادامه بده
                pass
        # اگر ساعت شروع کلاس موجود نبود یا مشکل داشت
        elif last_time:
            # اگر این کلاس قبلاً ساعت دستی داشت، از آن استفاده کن
            self.time_session.setTime(last_time)
        else:
            # ساعت پیش‌فرض
            self.time_session.setTime(QTime(12, 0))
            
        self.highlight_selected_class(item)

        self.load_sessions()
          # Load sessions for selected class
    def add_session_to_class(self):
        # بررسی انتخاب هنرجو و کلاس
        if not self.selected_class_id or not self.selected_student_id:
            QMessageBox.warning(self, "خطا", "لطفاً هنرجو و کلاس را انتخاب کنید.")
            return

        # استفاده از تاریخ شمسی انتخاب‌شده
        if not self.selected_shamsi_date:
            QMessageBox.warning(self, "خطا", "لطفاً تاریخ جلسه (شمسی) را انتخاب کنید.")
            return

        date = self.selected_shamsi_date
        time = self.time_session.time().toString("HH:mm")

        class_day, class_start_time = get_day_and_time_for_class(self.selected_class_id)
        session_time = self.time_session.time().toString("HH:mm")

        # --- دریافت پیکربندی ترم از کاربر ---
        cfg = {}
        dlg = TermConfigDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            cfg = dlg.get_config()  # dict: sessions_limit, tuition_fee, currency_unit, profile_id
        else:
            return  # کاربر لغو کرد
        

        # بررسی اینکه ساعت جلسه قبل از شروع کلاس نباشد
        if class_start_time:
            try:
                class_start_qtime = QTime.fromString(class_start_time, "HH:mm")
                session_qtime = self.time_session.time()
                if session_qtime < class_start_qtime:
                    QMessageBox.warning(self, "خطا", "ساعت شروع جلسه نمی‌تواند قبل از شروع کلاس مربوطه باشد.")
                    return
            except:
                pass  # اگر فرمت زمان مشکل داشت، ادامه بده

        # حالت ویرایش
        if self.is_editing:
            self.update_session()
            return

        # قبل از ثبت جلسه، اطمینان حاصل کن که ترم وجود دارد
        start_time = self.time_session.time().toString("HH:mm")
        self.selected_term_id = insert_student_term_if_not_exists(
            self.selected_student_id,
            self.selected_class_id,
            date,
            start_time,
            sessions_limit = cfg.get("sessions_limit"),
            tuition_fee    = cfg.get("tuition_fee"),
            currency_unit  = cfg.get("currency_unit"),
            profile_id     = cfg.get("profile_id"),
        )



        if self.selected_term_id is None:
            last_term_end_date = get_last_term_end_date(self.selected_student_id, self.selected_class_id)
            if last_term_end_date:
                QMessageBox.warning(self, "عدم امکان ایجاد ترم جدید",
                    f"ترم قبلی هنرجو در این کلاس در تاریخ {last_term_end_date} به پایان رسیده است.\n"
                    f"امکان ثبت ترم جدید از تاریخ {last_term_end_date} به بعد وجود دارد.")
            else:
                QMessageBox.warning(self, "عدم امکان ایجاد ترم جدید",
                    "امکان ایجاد ترم جدید در تاریخ انتخاب‌شده وجود ندارد.")
            return


        # بررسی اینکه آیا زمان جلسه خالی است یا خیر
        if is_class_slot_taken(self.selected_class_id, date, time):
            QMessageBox.warning(self, "تداخل کلاس", "در این روز و ساعت، کلاس برای هنرجوی دیگری رزرو شده است.")
            return

        if has_weekly_time_conflict(self.selected_student_id, class_day, session_time):
            QMessageBox.warning(self, "تداخل هفتگی", "هنرجو در این روز و ساعت کلاس دیگری دارد.")
            return
        
        # چک اسلات هفتگی استاد
        if has_teacher_weekly_time_conflict(self.selected_class_id, session_time):
            QMessageBox.warning(self, "تداخل با برنامهٔ استاد",
                "این استاد در همین روزِ هفته و همین ساعت، هنرجوی دیگری دارد.")
            return


        try:
            add_session(self.selected_class_id, self.selected_student_id, date, time)
            QMessageBox.information(self, "موفق", f"جلسه برای هنرجو با موفقیت در تاریخ {date} و ساعت {time} ثبت شد.")
            self.last_selected_time = self.time_session.time()
            self.last_time_per_class[self.selected_class_id] = self.last_selected_time
            self.refresh_session_counts()
            self.search_students()
            
        except sqlite3.IntegrityError as e:
            print("🔴 IntegrityError:", e)

            # 🧨 اگر جلسه درج نشد، ترم ساخته‌شده را حذف کن (مشروط به اینکه پرداختی نداشته باشد)
            delete_term_if_no_payments(self.selected_student_id, self.selected_class_id, self.selected_term_id)

            QMessageBox.warning(self, "جلسه تکراری", "این جلسه قبلاً ثبت شده است یا تداخل زمانی دارد.")
            return


        self.load_sessions()
        self.update_class_list()
        self.update_summary_bar()
        self.last_selected_date = self.selected_shamsi_date

    def load_sessions(self):
        self.list_sessions.setSortingEnabled(False)
        self.list_sessions.clear()
        if not self.selected_class_id:
            return

        rows = fetch_sessions_by_class(self.selected_class_id)

        def to_minutes(t: str) -> int:
            t = str(t).strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹","0123456789"))
            hh, mm = t.split(":"); return int(hh)*60 + int(mm)

        # قبلاً: rows = sorted(rows, key=lambda r: (str(r[2]).strip(), to_minutes(r[3])))
        # الان: سورت «اول زمان، بعد تاریخ»:
        rows = sorted(rows, key=lambda r: (to_minutes(r[3]), str(r[2]).strip()))

        for s_id, student_name, date_str, time_str, _ in rows:
            # منسجم: تاریخ جلوتر بیاید تا با سورت ذهنی هم‌راستا باشد
            text = f"{date_str} ساعت {time_str} - {student_name}"
            item = QListWidgetItem(text)
            item.setData(1, s_id)
            self.list_sessions.addItem(item)

    def delete_session_from_class(self, item):
        session_id = item.data(1)

        # قبل از هر چیز بپرس آیا می‌خواهی حذف شود
        reply = QMessageBox.question(self, "حذف جلسه", "آیا این جلسه حذف شود؟",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        
        session_info = get_session_by_id(session_id)
        if not session_info:
            QMessageBox.warning(self, "خطا", "اطلاعات جلسه یافت نشد.")
            return
        student_id, class_id, term_id = session_info
        # قبل از حذف جلسه، بررسی کن که ترم پرداختی دارد یا نه
        has_payment = not delete_term_if_no_payments(student_id, class_id, term_id)

        if has_payment:
            QMessageBox.warning(self, "حذف ممکن نیست",
                                "برای ترم این هنرجو پرداخت ثبت شده است. لطفاً ابتدا پرداخت‌ها را حذف کنید، سپس اقدام به حذف جلسه نمایید.")
            return

        # اگر پرداختی ندارد، حذف جلسه و پیام موفقیت
        delete_session(session_id)
        self.load_sessions()
        self.update_class_list()
        self.update_summary_bar()
        QMessageBox.information(self, "موفق", "جلسه و ترم مرتبط با موفقیت حذف شدند.")

        # ✅ شمارش جلسات هنرجویان را ریفرش کن و لیست جستجو را بازترسیم کن
        self.refresh_session_counts()
        self.search_students()

        self.last_selected_time = self.time_session.time()
        self.last_time_per_class[self.selected_class_id] = self.last_selected_time

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

        class_day, class_start_time = get_day_and_time_for_class(self.selected_class_id)
        session_time = self.time_session.time().toString("HH:mm")

        # بررسی اینکه ساعت جلسه قبل از شروع کلاس نباشد
        if class_start_time:
            try:
                class_start_qtime = QTime.fromString(class_start_time, "HH:mm")
                session_qtime = self.time_session.time()
                if session_qtime < class_start_qtime:
                    QMessageBox.warning(self, "خطا", "ساعت شروع جلسه نمی‌تواند قبل از شروع کلاس مربوطه باشد.")
                    return
            except:
                # اگر فرمت زمان مشکل داشت، ادامه بده
                pass

        # بررسی تداخل هفتگی
        if has_weekly_time_conflict(self.selected_student_id, class_day, session_time,
                                    exclude_session_id=self.selected_session_id):
            QMessageBox.warning(self, "تداخل هفتگی", "هنرجو در این روز و ساعت کلاس دیگری دارد.")
            return
        
        # چک اسلات هفتگی استاد
        if has_teacher_weekly_time_conflict(self.selected_class_id, time, exclude_session_id=self.selected_session_id):
            QMessageBox.warning(self, "تداخل با برنامهٔ استاد",
                "این استاد در همین روزِ هفته و همین ساعت، هنرجوی دیگری دارد.")
            return

        # بررسی تداخل زمان با هنرجوی دیگر
        if is_class_slot_taken(self.selected_class_id, date, time) and not self.is_editing:
            QMessageBox.warning(self, "تداخل کلاس", "در این روز و ساعت، کلاس برای هنرجوی دیگری رزرو شده است.")
            return

        # بررسی انتخاب کلاس و هنرجو
        if not self.selected_class_id or not self.selected_student_id:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا هنرجو و کلاس را انتخاب کنید.")
            return
        
        session_info = get_session_by_id(self.selected_session_id)
        if not session_info:
            QMessageBox.warning(self, "خطا", "اطلاعات جلسه یافت نشد.")
            return

        student_id, class_id, term_id = session_info

        try:
            update_session(
                self.selected_session_id,
                class_id,
                student_id,
                term_id,
                date,
                time
            )
            QMessageBox.information(self, "موفق", "جلسه با موفقیت ویرایش شد.")

            # اگر هنرجو هنوز ترمی نداشته، بساز
            insert_student_term_if_not_exists(self.selected_student_id, self.selected_class_id, date, time)

            # ✅ شمارش جلسات هنرجویان را ریفرش کن و لیست جستجو را بازترسیم کن
            self.refresh_session_counts()
            self.search_students()

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

    def update_class_list(self):
        """بروزرسانی لیست کلاس‌های هنرجو و تعداد جلسات ثبت‌شده"""
        self.load_student_classes()

    def update_summary_bar(self):
     """در صورت وجود نوار وضعیت، اطلاعات جلسات یا ترم‌ها را بروزرسانی می‌کند"""
    # فرض: self.statusBar یا یک QLabel دارید، آنجا اطلاعات جدید قرار می‌گیرد
    pass  # اگر وجود ندارد، لازم نیست چیزی بنویسی

    def highlight_selected_class(self, selected_item):
        for i in range(self.list_classes.count()):
            item = self.list_classes.item(i)
            widget = self.list_classes.itemWidget(item)
            if item == selected_item:
                widget.setStyleSheet(widget.styleSheet() + "border: 2px solid #0000FF;")  # آبی پررنگ
            else:
                # حذف Border انتخاب
                widget.setStyleSheet(widget.styleSheet().replace("border: 2px solid #0000FF;", "border: 1px solid #ccc;"))

    def manual_cleanup_expired_sessions(self):
        # ۰) لیست "پایان ترم"هایی که هنوز اعلان نشده‌اند
        expired = get_unnotified_expired_terms()
        if not expired:
            QMessageBox.information(self, "پاکسازی", "موردی یافت نشد؛ همه چیز قبلاً اعلان شده یا جلسه‌ای برای حذف وجود ندارد.")
            return

        # پیش‌نمایش + جمع‌آوری داده‌ها برای mark و delete
        lines = ["ترم‌های پایان‌یافته که «علامت‌گذاری و سپس حذف جلسات آینده» خواهند شد:"]
        to_mark = []
        term_ids = set()

        for student_id, class_id, student_name, national_code, class_name, day, term_id, session_date, session_time in expired:
            lines.append(f"• ترم #{term_id} — {student_name} | {class_name} ({day}) | {session_date} {session_time}")
            # ورودیِ mark_terms_as_notified همان فرمت قبلی:
            to_mark.append((term_id, student_id, class_id, session_date, session_time))
            term_ids.add(term_id)

        preview = "\n".join(lines)
        if QMessageBox.question(
            self, "تأیید عملیات",
            preview + "\n\nابتدا به‌عنوان «اعلان‌شده» ثبت و سپس جلسات آینده حذف شوند؟",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return

        # ۱) اول: ثبت اعلان (جدول notified_terms)
        try:
            mark_terms_as_notified(to_mark)
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"در ثبت اعلان (mark) مشکلی پیش آمد:\n{e}")
            return

        # ۲) بعد: حذف جلسات آیندهٔ همان ترم‌ها
        total_deleted = 0
        for term_id in term_ids:
            try:
                deleted = delete_sessions_for_term(term_id)  # طبق پیاده‌سازی تو: فقط جلسات آینده ترم را حذف می‌کند
                total_deleted += int(deleted or 0)
            except Exception:
                # اگر repo مقدار برنگرداند یا خطا داد، ادامه می‌دهیم ولی عدد حذف را اضافه نمی‌کنیم
                pass

        # ۳) اطلاع نتیجه و رفرش UI
        QMessageBox.information(
            self, "نتیجه پاکسازی",
            f"علامت‌گذاری {fa_digits(len(to_mark))} مورد انجام شد و مجموعاً {fa_digits(total_deleted)} جلسه حذف گردید."
        )

        self.load_sessions()
        self.update_class_list()
        self.update_summary_bar()
        # اختیاری: اگر می‌خواهی شمارش‌ها و لیست هنرجویان هم به‌روز شود:
        self.refresh_session_counts()
        self.search_students()
