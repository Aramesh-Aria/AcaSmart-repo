from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QMessageBox,QLabel
from PyQt5.QtCore import Qt
from student_manager import StudentManager
from teacher_manager import TeacherManager
from change_password_window import ChangeCredentialsWindow
from class_manager import ClassManager
from session_manager import SessionManager
import shutil
from db_helper import fetch_teachers
from pay_manager import PaymentManager
from settings_window import SettingsWindow
from attendance_window import AttendanceManager
from reports_window import ReportsWindow
from version import __version__
from pathlib import Path

class DashboardWindow(QWidget):
    def __init__(self, logged_in_mobile):
        super().__init__()
        self.logged_in_mobile = logged_in_mobile
        self.setWindowTitle("Admin Dashboard")
        self.setGeometry(150, 150, 400, 400)
        layout = QVBoxLayout()
        layout.setSpacing(12)
        button_style = "font-size: 15px; padding: 10px;"
        self.db_path = Path.home() / "AppData" / "Local" / "Amoozeshgah" / "academy.db"
        
        if not self.db_path.exists():
            QMessageBox.critical(self, "خطای دیتابیس", f"فایل دیتابیس یافت نشد:\n{self.db_path}")
            self.close()
            return

        # ----------- مدیریت‌ها ------------
        buttons_top = [
            ("🎓 مدیریت هنرجویان", self.open_student_manager),
            ("🧑‍🏫 مدیریت اساتید", self.open_teacher_manager),
            ("📅 مدیریت کلاس‌ها", self.open_class_manager),
            ("📆 مدیریت جلسات", self.open_session_manager),
            ("📋 حضور و غیاب", self.open_attndance_window),
            ("💰 ثبت پرداخت‌ها", self.open_payment_manager),

        ]

        for title, handler in buttons_top:
            btn = QPushButton(title)
            btn.setStyleSheet(button_style)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
            # ----------- ابزارهای مدیریتی ------------
            layout.addSpacing(20)  # فاصله بین بخش‌ها

            buttons_bottom = [
                ("📊 گزارش‌گیری", self.open_reports),
                ("📥 بکاپ‌گیری از دیتابیس", self.backup_database),
                ("📤 بازیابی بکاپ", self.restore_database),
                ("⚙️ تنظیمات آموزشگاه",self.open_setting_manager),
                ("🔑 تغییر رمز عبور", self.open_change_password),
                ("❌ خروج از برنامه", self.close),
            ]

        for title, handler in buttons_bottom:
            btn = QPushButton(title)
            btn.setStyleSheet(button_style)
            if handler:
                btn.clicked.connect(handler)
            layout.addWidget(btn)

        # لیبل نسخه اپلیکیشن
        version_label = QLabel(f"نسخه نرم‌افزار: {__version__}")
        version_label.setStyleSheet("color: gray; font-size: 12px; margin-top: 15px;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        self.setLayout(layout)

    def open_student_manager(self):
        self.student_window = StudentManager()
        self.student_window.show()

    def open_teacher_manager(self):
        self.teacher_window = TeacherManager()
        #با show() اون پنجره (ویجت) به کاربر نمایش داده می‌شهبا show() اون پنجره (ویجت) به کاربر نمایش داده می‌شه
        self.teacher_window.show()

    def open_change_password(self):
        self.change_password_window = ChangeCredentialsWindow(logged_in_mobile=self.logged_in_mobile)
        self.change_password_window.show()

    def open_class_manager(self):
        self.class_window = ClassManager()
        self.class_window.show()

    def open_session_manager(self):
        self.session_window = SessionManager()
        self.session_window.show()

    def open_payment_manager(self):
        self.payment_manager_window = PaymentManager()
        self.payment_manager_window.show()

    def open_setting_manager(self):
        self.setting_window = SettingsWindow()
        self.setting_window.show()

    def open_attndance_window(self):
        self.attendance_window = AttendanceManager()
        self.attendance_window.show()

    def backup_database(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self, "ذخیره بکاپ دیتابیس", "academy_backup.db",
                                                  "SQLite Files (*.db)", options=options)
        if filename:
            try:
                shutil.copyfile(self.db_path, filename)
                QMessageBox.information(self, "بکاپ‌گیری موفق", f"فایل بکاپ با موفقیت ذخیره شد:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "خطا در بکاپ‌گیری", f"مشکلی در ذخیره فایل بکاپ پیش آمد:\n{str(e)}")

    def restore_database(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(self, "انتخاب فایل بکاپ برای بازیابی", "",
                                                  "SQLite Files (*.db)", options=options)
        if filename:
            try:
                shutil.copyfile(filename, self.db_path)
                QMessageBox.information(self, "بازیابی موفق",
                                        "فایل بکاپ با موفقیت بازیابی شد.\n\nبرای اعمال تغییرات، لطفاً برنامه را ببندید و دوباره اجرا کنید.")
            except Exception as e:
                QMessageBox.critical(self, "خطا در بازیابی", f"مشکلی در بازیابی فایل پیش آمد:\n{str(e)}")

    def open_reports(self):
        self.reports_window = ReportsWindow()
        self.reports_window.show()