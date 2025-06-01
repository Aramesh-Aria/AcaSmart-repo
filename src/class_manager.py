from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout,
    QFormLayout, QTimeEdit, QMessageBox
)
from PyQt5.QtCore import QTime,Qt,QSize
from db_helper import (
    create_class, fetch_teachers_with_instruments, fetch_classes,
    class_exists, delete_class_by_id, is_class_has_sessions,
    get_instruments_for_teacher, get_class_by_id, update_class_by_id,does_teacher_have_time_conflict
)
from PyQt5.QtGui import QColor

class ClassManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت کلاس‌ها")
        self.setGeometry(300, 200, 500, 600)

        # Flag to distinguish create vs edit
        self.is_editing = False
        self.selected_class_id = None
        self.teachers_map = {}

        self.setLayout(self.build_ui())

        # Initial data load
        self.load_teachers()
        self.combo_teacher.currentIndexChanged.connect(self.update_instruments_for_teacher)
        self.update_instruments_for_teacher()  # Load instruments for first teacher
        self.load_classes()

    def build_ui(self):
        # Create fields
        self.input_name = QLineEdit()
        self.combo_teacher = QComboBox()
        self.combo_instrument = QComboBox()
        self.combo_day = QComboBox()
        self.combo_day.addItems([
            "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه",
            "چهارشنبه", "پنجشنبه", "جمعه"
        ])
        self.time_start = QTimeEdit()
        self.time_start.setTime(QTime(12, 0))
        self.time_end = QTimeEdit()
        self.time_end.setTime(QTime(20, 0))
        self.input_room = QLineEdit()

        # Buttons
        self.btn_create_class = QPushButton("➕ ایجاد کلاس")
        self.btn_create_class.clicked.connect(self.create_class)
        self.btn_clear = QPushButton("🧹 پاک‌سازی فرم")
        self.btn_clear.clicked.connect(self.clear_form)

        # List
        self.list_classes = QListWidget()
        self.list_classes.itemClicked.connect(self.load_class_into_form)
        self.list_classes.itemDoubleClicked.connect(self.delete_class)

        # class counts
        self.lbl_class_count = QLabel("تعداد نتایج: ۰ کلاس")
        self.lbl_class_count.setStyleSheet("font-size: 13px; color: gray; margin-top: 5px;")

        # Layouts
        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        form_layout.addRow(": نام کلاس", self.input_name)
        form_layout.addRow(": استاد", self.combo_teacher)
        form_layout.addRow(": ساز تدریسی", self.combo_instrument)
        form_layout.addRow(": روز هفته", self.combo_day)
        form_layout.addRow(": ساعت شروع", self.time_start)
        form_layout.addRow(": ساعت پایان", self.time_end)
        form_layout.addRow(": اتاق", self.input_room)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.btn_create_class)
        btn_layout.addWidget(self.btn_clear)

        # جستجوی پیشرفته
        self.btn_toggle_filter = QPushButton("فیلتر پیشرفته 🔽")
        self.btn_toggle_filter.clicked.connect(self.toggle_advanced_filter)

        # فیلدهای فیلتر
        self.filter_day = QComboBox()
        self.filter_day.addItems(["همه", "شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"])

        self.filter_instrument = QLineEdit()
        self.filter_instrument.setPlaceholderText("فیلتر ساز تدریسی")

        self.filter_teacher = QLineEdit()
        self.filter_teacher.setPlaceholderText("فیلتر نام استاد")

        self.filter_class_name = QLineEdit()
        self.filter_class_name.setPlaceholderText("فیلتر نام کلاس")

        # چیدمان فیلترها
        self.filter_widget = QWidget()
        filter_layout = QVBoxLayout()
        filter_layout.addWidget(QLabel("فیلتر بر اساس روز هفته:"))
        filter_layout.addWidget(self.filter_day)
        filter_layout.addWidget(QLabel("فیلتر بر اساس ساز تدریسی:"))
        filter_layout.addWidget(self.filter_instrument)
        filter_layout.addWidget(QLabel("فیلتر بر اساس نام استاد:"))
        filter_layout.addWidget(self.filter_teacher)
        filter_layout.addWidget(QLabel("فیلتر بر اساس نام کلاس:"))
        filter_layout.addWidget(self.filter_class_name)
        self.filter_widget.setLayout(filter_layout)
        self.filter_widget.hide()

        # اتصال تغییرات فیلترها به رفرش لیست
        self.filter_day.currentTextChanged.connect(self.load_classes)
        self.filter_instrument.textChanged.connect(self.load_classes)
        self.filter_teacher.textChanged.connect(self.load_classes)
        self.filter_class_name.textChanged.connect(self.load_classes)

        self.showMaximized()

        # Assemble
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(self.btn_toggle_filter)
        main_layout.addWidget(self.filter_widget)
        main_layout.addWidget(QLabel("لیست کلاس‌ها (برای حذف دوبار کلیک کنید):"))
        main_layout.addWidget(self.list_classes)
        main_layout.addWidget(self.lbl_class_count)

        return main_layout


    def clear_form(self):
        """ریست کردن فیلدهای ورودی و بازگشت به حالت اولیه"""
        self.input_name.clear()

        # برگرداندن استاد به اولین مورد
        self.combo_teacher.setCurrentIndex(0)
        # لود مجدد سازهای استاد اول
        self.update_instruments_for_teacher()
        # انتخاب اولین ساز (در صورتی که وجود داشته باشد)
        if self.combo_instrument.count() > 0:
            self.combo_instrument.setCurrentIndex(0)

        # ادامه‌ی پاکسازی بقیه فیلدها
        self.combo_day.setCurrentIndex(0)
        self.time_start.setTime(QTime(12, 0))
        self.time_end.setTime(QTime(20, 0))
        self.input_room.clear()

        # Reset editing flag & button text

        self.is_editing = False
        self.selected_class_id = None

        self.btn_create_class.setText("➕ ایجاد کلاس")
        self.list_classes.clearSelection()
        self.input_name.setFocus()

    def load_teachers(self):
        self.combo_teacher.clear()
        self.teachers_map = {}
        for tid, name, instruments in fetch_teachers_with_instruments():
            instruments = instruments if instruments else "بدون ساز"
            display_text = f"{name} ({instruments})"
            self.combo_teacher.addItem(display_text)
            self.teachers_map[display_text] = tid

    def update_instruments_for_teacher(self):

        self.combo_instrument.clear()

        teacher_text = self.combo_teacher.currentText()

        teacher_id = self.teachers_map.get(teacher_text)

        if teacher_id:

            insts = get_instruments_for_teacher(teacher_id)

            self.combo_instrument.addItems(insts or ["❌ هیچ سازی ثبت نشده"])

    def load_classes(self):
        selected_day = self.filter_day.currentText()
        filter_instrument = self.filter_instrument.text().strip().lower()
        filter_teacher = self.filter_teacher.text().strip().lower()
        filter_class_name = self.filter_class_name.text().strip().lower()

        raw_classes = fetch_classes()
        filtered = []

        for cls in raw_classes:
            class_id, name, teacher_name, instrument, day, start_time, end_time, room = cls

            if selected_day != "همه" and day != selected_day:
                continue
            if filter_instrument and filter_instrument not in instrument.lower():
                continue
            if filter_teacher and filter_teacher not in teacher_name.lower():
                continue
            if filter_class_name and filter_class_name not in name.lower():
                continue

            filtered.append(cls)

        # مرتب‌سازی بر اساس روز هفته
        week_order = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
        filtered.sort(key=lambda x: week_order.index(x[4]) if x[4] in week_order else 7)

        self.list_classes.clear()

        for cls in filtered:
            class_id, name, teacher_name, instrument, day, start_time, end_time, room = cls

            main_text = f"<b>{name}</b> - <span style='color:#444'>{teacher_name} - {instrument}</span>"
            detail_text = f"<span style='font-size:11px; color:#888'>{day} {start_time} - {end_time} | اتاق: {room}</span>"

            label = QLabel(f"{main_text}<br>{detail_text}")
            label.setTextFormat(Qt.RichText)
            label.setStyleSheet("""
                padding: 10px;
                line-height: 1.6;
                font-size: 13px;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin-bottom: 6px;
            """)
            label.setAttribute(Qt.WA_TransparentForMouseEvents)

            item = QListWidgetItem()
            item.setSizeHint(label.sizeHint())
            item.setData(1, class_id)

            self.list_classes.addItem(item)
            self.list_classes.setItemWidget(item, label)

        self.lbl_class_count.setText(f"تعداد نتایج: {len(filtered)} کلاس")

    def load_class_into_form(self, item):
        class_id = item.data(1)
        self.selected_class_id = class_id

        # بارگذاری اطلاعات کلاس از دیتابیس
        try:
            cls = get_class_by_id(class_id)
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در بارگذاری اطلاعات کلاس: {e}")
            return

        if not cls:
            QMessageBox.warning(self, "خطا", "اطلاعات کلاس یافت نشد.")
            return

        # مقداردهی اولیهٔ فیلدها
        name, teacher_id, instrument, day_str, start_str, end_str, room = cls
        self.input_name.setText(name)

        # تنظیم استاد بدون اجرای سیگنال (برای جلوگیری از دو بار بارگذاری ساز)
        self.combo_teacher.blockSignals(True)
        for idx in range(self.combo_teacher.count()):
            if self.teachers_map.get(self.combo_teacher.itemText(idx)) == teacher_id:
                self.combo_teacher.setCurrentIndex(idx)
                break
        self.combo_teacher.blockSignals(False)

        # بارگذاری دستی لیست سازها و تنظیم ساز کلاس
        self.update_instruments_for_teacher()
        if instrument:
            self.combo_instrument.setCurrentText(instrument)

        # تنظیم بقیهٔ فیلدها
        self.combo_day.setCurrentText(day_str)
        self.time_start.setTime(QTime.fromString(start_str, "HH:mm"))
        self.time_end.setTime(QTime.fromString(end_str, "HH:mm"))
        self.input_room.setText(room)

        # Switch to edit mode
        self.is_editing = True
        self.btn_create_class.setText("💾 ذخیره تغییرات")

    def create_class(self):
        # 1. خواندن مقادیر فرم
        name = self.input_name.text().strip()
        teacher_name = self.combo_teacher.currentText()
        teacher_id = self.teachers_map.get(teacher_name)
        day = self.combo_day.currentText()
        start_qt = self.time_start.time()
        end_qt = self.time_end.time()
        start_time = start_qt.toString("HH:mm")
        end_time = end_qt.toString("HH:mm")
        room = self.input_room.text().strip()
        instrument = self.combo_instrument.currentText()

        # 1. اعتبارسنجی استاد
        if not get_instruments_for_teacher(teacher_id):
            QMessageBox.warning(self, "خطا", "این استاد هیچ سازی برای تدریس ثبت نکرده است.")
            return

        # 2. اعتبارسنجی ساز
        if not instrument or "❌" in instrument:
            QMessageBox.warning(self, "خطا", "ساز تدریسی نامعتبر است یا برای این استاد ثبت نشده.")
            return

        # 3. اعتبارسنجی سایر فیلدها
        if not name or not teacher_id:
            QMessageBox.warning(self, "خطا", "لطفاً اطلاعات کلاس را کامل وارد کنید.")
            return

        # 4. اعتبارسنجی زمان (پایان پس از شروع)
        if start_qt >= end_qt:
            QMessageBox.warning(self, "خطا", "ساعت پایان باید بعد از ساعت شروع باشد.")
            return

        # 5. بررسی تداخل زمانی کلاس استاد
        if self.is_editing:
            conflict = does_teacher_have_time_conflict(teacher_id, day, start_time, end_time,
                                                        exclude_class_id=self.selected_class_id)
        else:
            conflict = does_teacher_have_time_conflict(teacher_id, day, start_time, end_time)

        if conflict:
            QMessageBox.warning(self, "تداخل زمانی", "استاد در این بازه زمانی کلاس دیگری دارد.")
            return

        try:
            # 5. مسیر ویرایش
            if self.is_editing:
                update_class_by_id(
                    self.selected_class_id,
                    name, teacher_id, day, start_time, end_time, room, instrument
                )
                QMessageBox.information(self, "موفق", "کلاس با موفقیت ویرایش شد.")
                self.is_editing = False

            # 6. مسیر ایجاد جدید
            else:
                if class_exists(teacher_id, day, start_time, end_time, room):
                    QMessageBox.warning(self, "کلاس تکراری", "کلاسی با این مشخصات قبلاً ثبت شده است.")
                    return

                create_class(name, teacher_id, day, start_time, end_time, room, instrument)
                QMessageBox.information(self, "موفق", "کلاس با موفقیت ثبت شد.")

        except Exception as e:
            QMessageBox.critical(self, "خطای پایگاه‌داده", f"خطا در ذخیره‌سازی: {e}")
            return

        # 7. پاک‌سازی فرم و بارگذاری مجدد لیست
        self.clear_form()
        self.load_classes()

    def delete_class(self, item):
        class_id = item.data(1)
        class_name = item.text()

        if is_class_has_sessions(class_id):
            QMessageBox.warning(self, "خطا",
                                f"امکان حذف کلاس «{class_name}» وجود ندارد چون جلسه‌ای برای آن ثبت شده است.")
            return

        reply = QMessageBox.question(self, "حذف کلاس", f"آیا از حذف کلاس «{class_name}» مطمئن هستید؟",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            delete_class_by_id(class_id)
            self.load_classes()

    def update_instruments_for_teacher(self):
        self.combo_instrument.clear()
        teacher_name = self.combo_teacher.currentText()
        teacher_id = self.teachers_map.get(teacher_name)
        if teacher_id:
            instruments = get_instruments_for_teacher(teacher_id)
            self.combo_instrument.addItems(instruments if instruments else ["❌ هیچ سازی ثبت نشده"])

    def toggle_advanced_filter(self):
        if self.filter_widget.isVisible():
            self.filter_widget.hide()
            self.btn_toggle_filter.setText("فیلتر پیشرفته 🔽")
        else:
            self.filter_widget.show()
            self.btn_toggle_filter.setText("فیلتر پیشرفته 🔼")
