from data.settings_repo import get_setting, get_setting_bool, set_setting, set_setting_bool
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton, QMessageBox, QComboBox
import re
from utils import currency_label

def _digits_only(text: str) -> int:
    """فقط ارقام را نگه می‌دارد (کاما/فاصله/حروف حذف)."""
    if text is None:
        return 0
    s = str(text)
    digits = ''.join(re.findall(r'\d+', s))
    return int(digits) if digits else 0

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("تنظیمات آموزشگاه")
        self.setGeometry(350, 250, 300, 200)

        layout = QFormLayout()

        # شهریه هر ترم
        self.input_term_fee = QLineEdit()
        # تومان خام در DB
        fee_toman = int(get_setting("term_fee", "6000000"))
        # واحد فعلی UI (از تنظیمات ذخیره‌شده)
        current_unit = get_setting("currency_unit", "تومان")
        ui_unit = current_unit if current_unit in ["تومان", "ریال"] else "تومان"

        # نمایش: اگر ریال است، ×۱۰؛ اگر تومان است همان عدد
        display_fee = fee_toman * 10 if ui_unit == "ریال" else fee_toman
        self.input_term_fee.setText(str(display_fee))
        self.input_term_fee.setPlaceholderText(f"مبلغ شهریه ({ui_unit})")

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
        self.combo_currency.setCurrentText(ui_unit)
        # نگه‌داشتن واحد قبلی برای تبدیل درست نمایش
        self._last_unit = ui_unit

        # با تغییر واحد، صفر اضافه/کم شود اما تومان خام ثابت بماند
        self.combo_currency.currentTextChanged.connect(self._on_currency_changed)
        layout.addRow(": واحد پول", self.combo_currency)

        # تنظیم پیامک فعال یا غیرفعال
        self.combo_sms_enabled = QComboBox()
        self.combo_sms_enabled.addItems(["فعال", "غیرفعال"])
        is_sms_on = get_setting_bool("sms_enabled", True)
        self.combo_sms_enabled.setCurrentIndex(0 if is_sms_on else 1)
        layout.addRow(": ارسال پیامک", self.combo_sms_enabled)

        # دکمه ذخیره
        self.btn_save = QPushButton("ذخیره تنظیمات")
        self.btn_save.clicked.connect(self.save_settings)
        layout.addRow(self.btn_save)

        self.setLayout(layout)
    def _on_currency_changed(self, new_unit: str):
        """با عوض شدن تومان/ریال، نمایش فیلد شهریه را بدون تغییر تومان خام اصلاح کن."""
        old_unit = self._last_unit
        if new_unit == old_unit:
            return

        # 1) عدد فعلی را بر اساس واحد قبلی به تومان خام تبدیل کن
        current_display = _digits_only(self.input_term_fee.text())
        if old_unit == "ریال":
            fee_toman = int(round(current_display / 10))
        else:  # "تومان"
            fee_toman = current_display

        # 2) حالا بر اساس واحد جدید دوباره برای نمایش تنظیم کن
        if new_unit == "ریال":
            new_display = fee_toman * 10
        else:  # "تومان"
            new_display = fee_toman

        self.input_term_fee.setText(str(new_display))
        self.input_term_fee.setPlaceholderText(f"مبلغ شهریه ({new_unit})")
        self._last_unit = new_unit

    def save_settings(self):
        # --- مبلغ شهریه: همیشه تومان خام در DB ذخیره شود ---
        fee_text = self.input_term_fee.text().strip()
        display_val = _digits_only(fee_text)
        ui_unit_now = self.combo_currency.currentText()

        if display_val <= 0:
            QMessageBox.warning(self, "خطا", "لطفاً یک عدد صحیح مثبت برای شهریه وارد کنید.")
            return

        # به تومان تبدیل کن
        fee_toman = int(round(display_val / 10)) if ui_unit_now == "ریال" else display_val

        # --- تعداد جلسات ---
        sessions_text = self.input_term_sessions.text().strip()
        try:
            sessions = int(sessions_text)
            if sessions <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "خطا", "لطفاً یک عدد صحیح مثبت برای تعداد جلسات وارد کنید.")
            return

        # --- ذخیره‌سازی ---
        set_setting("term_fee", fee_toman)                     # همیشه تومان
        set_setting("term_session_count", sessions)
        set_setting("currency_unit", ui_unit_now)              # "تومان" یا "ریال"
        set_setting_bool("sms_enabled", self.combo_sms_enabled.currentIndex() == 0)

        QMessageBox.information(self, "موفق", "تنظیمات با موفقیت ذخیره شد.")
        self.close()