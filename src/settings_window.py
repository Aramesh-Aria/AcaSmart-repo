from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton, QMessageBox, QComboBox
from db_helper import get_setting, set_setting

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تنظیمات آموزشگاه")
        self.setGeometry(350, 250, 300, 200)

        layout = QFormLayout()

        # شهریه هر ترم
        self.input_term_fee = QLineEdit()
        current_fee = get_setting("term_fee", "6000000")
        self.input_term_fee.setText(str(current_fee))
        self.input_term_fee.setPlaceholderText("مبلغ شهریه (تومان)")
        layout.addRow(": شهریه هر ترم", self.input_term_fee)

        # تعداد جلسات هر ترم
        self.input_term_sessions = QLineEdit()
        current_sessions = get_setting("term_session_count", "12")
        self.input_term_sessions.setText(str(current_sessions))
        self.input_term_sessions.setPlaceholderText("تعداد جلسات هر ترم")
        layout.addRow(": تعداد جلسات هر ترم", self.input_term_sessions)

        # واحد پول
        self.combo_currency = QComboBox()
        self.combo_currency.addItems(["تومان", "ریال"])
        current_unit = get_setting("currency_unit", "تومان")
        self.combo_currency.setCurrentText(current_unit if current_unit in ["تومان", "ریال"] else "تومان")
        layout.addRow(": واحد پول", self.combo_currency)

        # تنظیم پیامک فعال یا غیرفعال
        self.combo_sms_enabled = QComboBox()
        self.combo_sms_enabled.addItems(["فعال", "غیرفعال"])
        current_sms_setting = get_setting("sms_enabled", "فعال")
        self.combo_sms_enabled.setCurrentText(current_sms_setting if current_sms_setting in ["فعال", "غیرفعال"] else "فعال")
        layout.addRow(": ارسال پیامک", self.combo_sms_enabled)

        # دکمه ذخیره
        self.btn_save = QPushButton("ذخیره تنظیمات")
        self.btn_save.clicked.connect(self.save_settings)
        layout.addRow(self.btn_save)

        self.setLayout(layout)

    def save_settings(self):
        # اعتبارسنجی مبلغ
        fee_text = self.input_term_fee.text().strip()
        try:
            fee = int(fee_text)
            if fee <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "خطا", "لطفاً یک عدد صحیح مثبت برای شهریه وارد کنید.")
            return

        # اعتبارسنجی تعداد جلسات
        sessions_text = self.input_term_sessions.text().strip()
        try:
            sessions = int(sessions_text)
            if sessions <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "خطا", "لطفاً یک عدد صحیح مثبت برای تعداد جلسات وارد کنید.")
            return

        # ذخیره‌سازی تنظیمات
        set_setting("term_fee", fee)
        set_setting("term_session_count", sessions)
        set_setting("currency_unit", self.combo_currency.currentText())
        set_setting("sms_enabled", self.combo_sms_enabled.currentText())

        QMessageBox.information(self, "موفق", "تنظیمات با موفقیت ذخیره شد.")
        self.close()
