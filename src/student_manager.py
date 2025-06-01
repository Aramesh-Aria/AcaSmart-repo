from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QListWidget, QListWidgetItem, QComboBox, QFormLayout,QDialog, QToolButton, QStyle
)
from PyQt5.QtCore import Qt

from db_helper import (insert_student, student_national_code_exists,get_student_by_id,
                       update_student_by_id,delete_student_by_id,fetch_students,
                       is_national_code_exists_for_other)

import jdatetime
from shamsi_date_popup import ShamsiDatePopup

class StudentManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت هنرجویان")
        self.setGeometry(200, 200, 500, 600)


        layout = QVBoxLayout()
        layout.setSpacing(10)  # فاصله بین اجزا
        layout.setContentsMargins(15, 15, 15, 15)  # فاصله از لبه‌ها


        # get students data
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("نام و نام خانوادگی")
        self.input_name.textChanged.connect(self.check_form_validity)
        # get student's father name
        self.input_father_name = QLineEdit()
        self.input_father_name.setPlaceholderText("نام پدر")
        self.input_father_name.textChanged.connect(self.check_form_validity)
        # student age
        self.input_birth_date = QLineEdit()
        self.input_birth_date.setPlaceholderText("تاریخ تولد (شمسی)")
        self.input_birth_date.setReadOnly(True)
        # آیکن تقویم کنار فیلد تاریخ تولد
        calendar_btn = QToolButton()
        calendar_btn.setIcon(self.style().standardIcon(QStyle.SP_DesktopIcon))
        calendar_btn.setCursor(Qt.PointingHandCursor)
        calendar_btn.setStyleSheet("border: none; padding: 0px;")
        calendar_btn.clicked.connect(self.show_calendar_popup)

        self.input_birth_date.setTextMargins(0, 0, 25, 0)
        calendar_btn.setParent(self.input_birth_date)
        calendar_btn.move(self.input_birth_date.rect().right() - 20, (self.input_birth_date.height() - 16) // 2)
        calendar_btn.resize(20, 20)


        self.combo_gender = QComboBox()
        self.combo_gender.setPlaceholderText("جنسیت")
        self.combo_gender.addItems(["مذکر", "مونث"])
        self.combo_gender.setCurrentIndex(0)
        self.combo_gender.currentTextChanged.connect(self.check_form_validity)

        self.input_national_code = QLineEdit()
        self.input_national_code.setPlaceholderText("کد ملی هنرجو")
        self.input_national_code.textChanged.connect(self.check_form_validity)

        self.input_phone = QLineEdit()
        self.input_phone.setPlaceholderText("09*********")
        self.input_phone.textChanged.connect(self.check_form_validity)

        # دکمه افزودن
        self.btn_add = QPushButton("➕ افزودن هنرجو ")
        self.btn_add.clicked.connect(self.add_student)
        self.btn_add.setFixedHeight(40)
        self.btn_add.setStyleSheet("font-size: 14px;")
        self.btn_add.setEnabled(False)

        # دکمه ویرایش
        self.btn_update = QPushButton("✏ ویرایش اطلاعات ️")
        self.btn_update.clicked.connect(self.update_student)
        self.btn_update.setEnabled(False)#اول کار غیر فعاله
        self.btn_update.setFixedHeight(40)
        self.btn_update.setStyleSheet("font-size: 14px;")

        # دکمه پاک‌سازی فرم
        self.btn_clear = QPushButton("🧹 پاک‌سازی فرم ")
        self.btn_clear.clicked.connect(self.clear_form)

        # search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجو بر اساس نام و نام خانوادگی هنرجو")
        #با textChanged.connect(...)، هر تغییری در متن باعث اجرای تابع search_students می‌شه
        self.search_input.textChanged.connect(lambda text: self.search_students(text))
        # جستجو بر اساس جنسیت
        self.filter_gender = QComboBox()
        self.filter_gender.addItems(["همه", "مذکر", "مونث"])
        self.filter_gender.currentTextChanged.connect(lambda: self.search_students(self.search_input.text()))
        # جستجو بر اساس کد ملی
        self.filter_national_code = QLineEdit()
        self.filter_national_code.setPlaceholderText("فیلتر کد ملی")
        self.filter_national_code.textChanged.connect(lambda: self.search_students(self.search_input.text()))
        # مرتب سازی جسجتو با combobox
        self.sort_by = QComboBox()
        self.sort_by.addItems(["مرتب‌سازی بر اساس نام", "مرتب‌سازی بر اساس سن", "مرتب‌سازی بر اساس کد ملی"])
        self.sort_by.currentIndexChanged.connect(lambda: self.search_students(self.search_input.text()))

        # لیست هنرجویان
        self.list_students = QListWidget()
        self.list_students.itemClicked.connect(self.fill_form)
        self.list_students.itemDoubleClicked.connect(self.delete_student)

        # شمارش
        self.lbl_count = QLabel()
        self.lbl_count.setStyleSheet("font-size: 13px; color: gray;")


        #چینش در لایه اصلی
        form_layout = QFormLayout()
        form_layout.addRow(": نام هنرجو", self.input_name)
        form_layout.addRow(": نام پدر", self.input_father_name)
        form_layout.addRow(": تاریخ تولد", self.input_birth_date)
        form_layout.addRow(": جنسیت", self.combo_gender)
        form_layout.addRow(": کد ملی", self.input_national_code)
        form_layout.addRow(": شماره تلفن", self.input_phone)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_update)
        layout.addLayout(btn_layout) # move this if you want to change add and edit location buttons
        layout.addWidget(self.btn_clear)

        #جستجو
        self.btn_advanced = QPushButton("فیلتر پیشرفته 🔽")
        self.btn_advanced.clicked.connect(self.toggle_advanced)
        layout.addWidget(self.btn_advanced)

        self.adv_widget = QWidget()
        adv_layout = QVBoxLayout()
        # نام و نام خانوادگی
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel(": جستجوی نام"))
        search_layout.addWidget(self.search_input)
        adv_layout.addLayout(search_layout)

        # جنسیت
        gender_layout = QHBoxLayout()
        gender_layout.addWidget(QLabel(": جنسیت"))
        gender_layout.addWidget(self.filter_gender)
        adv_layout.addLayout(gender_layout)

        # کد ملی
        national_code_layout = QHBoxLayout()
        national_code_layout.addWidget(QLabel(": کد ملی"))
        national_code_layout.addWidget(self.filter_national_code)
        adv_layout.addLayout(national_code_layout)

        # مرتب‌سازی
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel(": مرتب‌سازی"))
        sort_layout.addWidget(self.sort_by)
        adv_layout.addLayout(sort_layout)

        self.adv_widget.setLayout(adv_layout)
        layout.addWidget(self.adv_widget)
        self.adv_widget.hide()


        layout.addWidget(QLabel("لیست هنرجویان (برای حذف دوبار کلیک کنید):"))
        layout.addWidget(self.list_students)



        # students count label
        self.lbl_count = QLabel("تعداد هنرجویان: ۰ نفر")
        self.lbl_count.setStyleSheet("font-size: 13px; color: gray; margin-top: 5px;")
        layout.addWidget(self.lbl_count)

        self.setLayout(layout)

        # داده‌ها
        self.selected_student_id = None

        self.students_data = [] # جلوگیری از AttributeError در جستجو

        # بارگزاری اولیه
        self.load_students()
        self.check_form_validity()

        self.showMaximized()

    def add_student(self):
        """'
        مقدارها رو از فرم می‌گیره
بررسی می‌کنه همه فیلدها پر شده باشن
مطمئن می‌شه سن عددی هست
در دیتابیس ذخیره می‌کنه
پیام موفقیت می‌ده
        فرم رو پاک می‌کنه برای وارد کردن نفر بعدی
        '"""
        name = self.input_name.text().strip()
        father_name = self.input_father_name.text().strip()
        gender = self.combo_gender.currentText()
        national_code = self.input_national_code.text().strip()
        phone = self.input_phone.text().strip()

        # تاریخ تولد
        birth_str = self.input_birth_date.text().strip()

        # بررسی تکراری بودن هنرجو
        if student_national_code_exists(national_code):
            QMessageBox.warning(self, "خطا", "این هنرجو یا کد ملی قبلاً ثبت شده است.")
            return

        # بررسی شماره تلفن
        if not phone or not phone.isdigit() or len(phone) != 11:
            QMessageBox.warning(self, "خطا", "شماره تلفن باید وارد شده، ۱۱ رقمی و فقط عدد باشد.")
            return

        insert_student(name, birth_str, gender, national_code, phone, father_name)

        QMessageBox.information(self, "موفق", "هنرجو با موفقیت اضافه شد.")
        self.clear_form()
        self.input_name.setFocus()
        self.load_students()


    def load_students(self):
        """Load all students and update internal list and UI."""

        # first clear current list
        self.list_students.clear()

        # فرض بر اینه که fetch_students() تابع جدیدی هست که (id, name) برمی‌گردونه
        rows = fetch_students()
        self.students_data = sorted(rows, key=lambda x: (x[1].lower(), x[4]))  # مرتب‌سازی بر اساس نام و کد ملی
        # for every student in items create a text like نام هنرجو (استاد: نام استاد)
        for student_id, name, gender, birth_date, national_code in self.students_data:
            # محاسبه سن از تاریخ تولد شمسی
            birth_jdate = jdatetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
            today_jdate = jdatetime.date.today()
            age = today_jdate.year - birth_jdate.year - (
                        (today_jdate.month, today_jdate.day) < (birth_jdate.month, birth_jdate.day))

            display_text = f"{name} - سن: {age} - کد ملی: {national_code}"

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, student_id)
            self.list_students.addItem(item)

        # update student count label
        self.lbl_count.setText(f"تعداد هنرجویان: {len(rows)} نفر")

    def search_students(self, text):
        """allow user to search a name in field"""
        #هر بار قبل از جستجو لیست رو تازه کن
        #لیست کامل هنرجویان از دیتابیس خونده بشه,سپس فیلتر روی داده‌های جدید انجام بشه
        # self.load_students()
        query = text.strip().lower()
        selected_gender = self.filter_gender.currentText()
        national_code_query = self.filter_national_code.text().strip()
        filtered_students = []

        self.list_students.clear()

        #از روی self.students_data عبور می‌کنی
        for student in self.students_data:
            student_id, name, gender, birth_date, national_code = student

            birth_jdate = jdatetime.datetime.strptime(birth_date, "%Y-%m-%d").date()
            today_jdate = jdatetime.date.today()
            age = today_jdate.year - birth_jdate.year - (
                        (today_jdate.month, today_jdate.day) < (birth_jdate.month, birth_jdate.day))

            if (query in name.lower() and
                    (selected_gender == "همه" or gender == selected_gender) and
                    national_code_query in national_code):
                filtered_students.append((student_id, name, gender, age, national_code))

        # مرتب‌سازی
        sort_criteria = self.sort_by.currentText()
        if sort_criteria == "مرتب‌سازی بر اساس نام":
            filtered_students.sort(key=lambda x: x[1].lower())
        elif sort_criteria == "مرتب‌سازی بر اساس سن":
            filtered_students.sort(key=lambda x: x[3])  # سن
        elif sort_criteria == "مرتب‌سازی بر اساس کد ملی":
            filtered_students.sort(key=lambda x: x[4])  # کد ملی

        for student_id, name, gender, age, national_code in filtered_students:
            display_text = f"{name} - سن: {age} - کد ملی: {national_code}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, student_id)
            self.list_students.addItem(item)

        # update student count label
        self.lbl_count.setText(f"تعداد نتایج: {self.list_students.count()} نفر")

    def fill_form(self, item):
        """پر کردن فرم با داده‌های دانشجو زمانی که روی آیتم کلیک می‌شود."""
        self.selected_student_id = item.data(Qt.UserRole)
        data = get_student_by_id(self.selected_student_id)
        if not data:
            return

        name, birth_date_str, gender, national_code, phone, father_name = data
        self.input_name.setText(name)
        self.input_father_name.setText(father_name)
        self.input_birth_date.setText(birth_date_str)

        self.combo_gender.setCurrentText(gender)
        self.input_national_code.setText(national_code)
        self.input_phone.setText(phone)
        self.btn_update.setEnabled(True)
        self.check_form_validity()

    def update_student(self):
        """ویرایش اطلاعات هنرجو"""
        if not self.selected_student_id:
            return

        name = self.input_name.text().strip()
        father_name = self.input_father_name.text().strip()
        gender = self.combo_gender.currentText()
        national_code = self.input_national_code.text().strip()
        phone = self.input_phone.text().strip()

        # دریافت تاریخ تولد از QDateEdit و تبدیل به شمسی
        birth_str = self.input_birth_date.text().strip()

        # بررسی تکراری نبودن کد ملی برای هنرجوی دیگر
        if is_national_code_exists_for_other("students", national_code, self.selected_student_id):
            QMessageBox.warning(self, "خطا", "کد ملی تکراری است.")
            return

        # بررسی اعتبار شماره تلفن
        if not phone or not phone.isdigit() or len(phone) != 11:
            QMessageBox.warning(self, "خطا", "شماره تلفن باید وارد شده، ۱۱ رقمی و فقط عدد باشد.")
            return

        # به‌روزرسانی اطلاعات در دیتابیس
        update_student_by_id(self.selected_student_id, name, birth_str, gender, national_code, phone, father_name)

        QMessageBox.information(self, "موفق", "اطلاعات هنرجو ویرایش شد.")
        self.clear_form()
        self.load_students()


    def delete_student(self, item):
        """delete student with double click"""
        student_id = item.data(Qt.UserRole)
        name = item.text()
        # show some massage for delete confirmation
        reply = QMessageBox.question(self, "حذف هنرجو", f"آیا مطمئنید می‌خواهید '{name}' را حذف کنید؟",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            delete_student_by_id(student_id)
            self.clear_form()
            self.load_students()

    def clear_form(self):
        """clear datas from inputs"""
        self.input_name.clear()
        self.input_father_name.clear()
        self.input_birth_date.clear()
        self.combo_gender.setCurrentIndex(0)
        self.input_national_code.clear()
        self.input_phone.clear()
        self.selected_student_id = None
        self.btn_update.setEnabled(False)
        self.check_form_validity()


    def check_form_validity(self):
        name = self.input_name.text().strip()
        father_name = self.input_father_name.text().strip()
        national_code = self.input_national_code.text().strip()
        phone = self.input_phone.text().strip()
        phone_valid = phone.isdigit() and len(phone) == 11
        birth_text = self.input_birth_date.text().strip()
        try:
            birth_date_valid = bool(birth_text) and jdatetime.datetime.strptime(birth_text, "%Y-%m-%d")
        except Exception:
            birth_date_valid = False

        is_valid = bool(name and father_name and national_code and phone_valid and birth_date_valid)
        self.btn_add.setEnabled(is_valid and self.selected_student_id is None)
        self.btn_update.setEnabled(is_valid and self.selected_student_id is not None)

    def toggle_advanced(self):
        if self.adv_widget.isHidden():
            self.adv_widget.show()
            self.btn_advanced.setText("فیلتر پیشرفته 🔼")
            self.search_input.setFocus()  # 🔍 فوکوس روی فیلد جستجو
        else:
            self.adv_widget.hide()
            self.btn_advanced.setText("فیلتر پیشرفته 🔽")

    def show_calendar_popup(self, event):
        dialog = ShamsiDatePopup(self)
        if dialog.exec_() == QDialog.Accepted:
            selected_date = dialog.get_selected_date()
            self.input_birth_date.setText(selected_date)
            self.check_form_validity()
            self.input_phone.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        for child in self.input_birth_date.children():
            if isinstance(child, QToolButton):
                child.move(self.input_birth_date.rect().right() - 20, (self.input_birth_date.height() - 16) // 2)
