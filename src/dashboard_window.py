from data.db import get_connection
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QMessageBox, QLabel,QApplication
from PySide6.QtCore import Qt
import shutil
from version import __version__
from paths import DB_PATH
import logging
import sqlite3

class DashboardWindow(QWidget):
    def __init__(self, logged_in_mobile):
        super().__init__()
        self.logged_in_mobile = logged_in_mobile
        self.setWindowTitle("Admin Dashboard")
        self.resize(1100, 650)  # اندازه ثابت داشبورد
        
        # Apply theme-based icon
        try:
            from theme_manager import apply_theme_icon,get_theme_icon
            apply_theme_icon(self)
            self.setWindowIcon(get_theme_icon())
        except Exception as e:
            print(f"⚠️ Could not apply theme icon to dashboard window: {e}")
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        button_style = "font-size: 15px; padding: 10px;"
        self.db_path = DB_PATH  # فقط برای نمایش/استفاده‌ی read-only از مسیر

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
        layout.addSpacing(20)

        buttons_bottom = [
            ("💼 پروفایل‌های شهریه", self.open_pricing_profile_manager),
            ("📊 گزارش‌گیری", self.open_reports),
            ("📥 بکاپ‌گیری از دیتابیس", self.backup_database),
            ("📤 بازیابی بکاپ", self.restore_database),
            ("⚙️ تنظیمات آموزشگاه", self.open_setting_manager),
            ("📲 ارسال پیامک به هنرجویان", self.open_sms_notification_manager),
            ("🔑 تغییر رمز عبور", self.open_change_password),
            ("❌ خروج از برنامه", self.close),
        ]

        for title, handler in buttons_bottom:
            btn = QPushButton(title)
            btn.setStyleSheet(button_style)
            if handler:
                btn.clicked.connect(handler)
            layout.addWidget(btn)

        version_label = QLabel(f"نسخه نرم‌افزار: {__version__}")
        version_label.setStyleSheet("color: gray; font-size: 12px; margin-top: 5px;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        info_label = QLabel("ایمیل توسعه دهنده جهت ارتباط: aramesh_aria@yahoo.com")
        info_label.setStyleSheet("color: gray; font-size: 12px; margin-top: 2px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        # گرفتن ابعاد صفحه
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        # محاسبه مختصات مرکز
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        # جابه‌جایی به مرکز
        self.move(x, y)

    def open_student_manager(self):
        from student_manager import StudentManager
        self.student_window = StudentManager()
        self.student_window.show()

    def open_teacher_manager(self):
        from teacher_manager import TeacherManager
        self.teacher_window = TeacherManager()
        self.teacher_window.show()

    def open_change_password(self):
        from change_password_window import ChangeCredentialsWindow
        self.change_password_window = ChangeCredentialsWindow(logged_in_mobile=self.logged_in_mobile)
        self.change_password_window.show()

    def open_class_manager(self):
        from class_manager import ClassManager
        self.class_window = ClassManager()
        self.class_window.show()

    def open_session_manager(self):
        from session_manager import SessionManager
        self.session_window = SessionManager()
        self.session_window.show()

    def open_payment_manager(self):
        from pay_manager import PaymentManager
        self.payment_manager_window = PaymentManager()
        self.payment_manager_window.show()

    def open_setting_manager(self):
        from settings_window import SettingsWindow
        self.setting_window = SettingsWindow()
        self.setting_window.show()

    def open_attndance_window(self):
        from attendance_window import AttendanceManager
        self.attendance_window = AttendanceManager()
        self.attendance_window.show()

    def backup_database(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(self, "ذخیره بکاپ دیتابیس", "acasmart_backup.db",
                                                  "SQLite Files (*.db)", options=options)
        if filename:
            try:
                logging.info(f"📥 عملیات بکاپ‌گیری آغاز شد. مسیر دیتابیس مبدا: {self.db_path}")
                # استفاده از API بکاپ SQLite تا با حالت WAL هم سازگار باشد
                with get_connection() as src_conn:
                    dst_conn = sqlite3.connect(filename)
                    try:
                        src_conn.backup(dst_conn)
                    finally:
                        dst_conn.close()
                logging.info(f"✅ فایل بکاپ با موفقیت در {filename} ذخیره شد.")
                QMessageBox.information(self, "بکاپ‌گیری موفق", f"فایل بکاپ با موفقیت ذخیره شد:\n{filename}")
            except Exception as e:
                logging.error(f"❌ خطا در بکاپ‌گیری: {str(e)}")
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
        from reports_window import ReportsWindow
        self.reports_window = ReportsWindow()
        self.reports_window.show()

    def open_sms_notification_manager(self):
        from sms_notification_window import SmsNotificationWindow
        self.open_sms_notification_window = SmsNotificationWindow()
        self.open_sms_notification_window.show()

    def open_pricing_profile_manager(self):
        from pricing_profile_manager import PricingProfileManager
        self.pricing_profile_window = PricingProfileManager()
        self.pricing_profile_window.show()