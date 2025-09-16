from data.db import get_connection
from data.profiles_repo import create_pricing_profile, list_pricing_profiles
from data.settings_repo import get_setting
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QDialogButtonBox, QLabel, QLineEdit, QSpinBox, QCheckBox,QAbstractItemView
)
from PySide6.QtCore import Qt
from utils import currency_label, format_currency_with_unit, parse_user_amount_to_toman

class PricingProfileDialog(QDialog):
    """
    دیالوگ افزودن/ویرایش پروفایل شهریه
    mode: 'add' | 'edit'
    data (برای edit): dict(id, name, sessions_limit, tuition_fee_toman, is_default)
                        tuition_fee_toman
    """
    def __init__(self, mode='add', data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("پروفایل شهریه")
        self.mode = mode
        self.data = data or {}
        lay = QVBoxLayout(self)

        # نام
        row_name = QHBoxLayout()
        row_name.addWidget(QLabel( ": نام پروفایل "))
        self.ed_name = QLineEdit(self.data.get("name", ""))
        row_name.addWidget(self.ed_name)
        lay.addLayout(row_name)

        # سقف جلسات
        row_sess = QHBoxLayout()
        row_sess.addWidget(QLabel(": تعداد جلسات "))
        self.sp_sessions = QSpinBox()
        self.sp_sessions.setRange(1, 100)
        self.sp_sessions.setValue(int(self.data.get("sessions_limit",
                           int(get_setting("term_session_count", 12)))))
        row_sess.addWidget(self.sp_sessions)
        lay.addLayout(row_sess)

        # واحد نمایش فعلی (فقط لیبل)
        row_unit = QHBoxLayout()
        row_unit.addWidget(QLabel(": واحد نمایش"))
        self.lbl_unit = QLabel(currency_label())  # "تومان" یا "ریال"
        row_unit.addWidget(self.lbl_unit)
        row_unit.addStretch(1)
        lay.addLayout(row_unit)

        # شهریه (نمایش/ورود برحسب واحد فعلی UI)
        row_fee = QHBoxLayout()
        row_fee.addWidget(QLabel(": شهریه ترم"))
        self.sp_fee = QSpinBox()
        self.sp_fee.setRange(0, 1_000_000_000)
        self.sp_fee.setSingleStep(10000)

        init_fee_toman = int(self.data.get(
            "tuition_fee_toman",
            int(get_setting("term_fee", get_setting("term_tuition", 6000000)))
        ))
        # اگر UI روی «ریال» است، برای نمایش ×۱۰
        disp_fee = init_fee_toman * 10 if currency_label() == "ریال" else init_fee_toman
        self.sp_fee.setValue(int(disp_fee))

        row_fee.addWidget(self.sp_fee)
        lay.addLayout(row_fee)

        # پیش‌فرض؟
        self.chk_default = QCheckBox("قرار دادن به عنوان پروفایل پیش‌فرض")
        self.chk_default.setChecked(bool(self.data.get("is_default", 0)))
        lay.addWidget(self.chk_default)

        # دکمه‌ها
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def get_values(self):
        # مقدار ورودی کاربر (برحسب واحد فعلی UI) → تومان خام برای DB
        fee_toman = parse_user_amount_to_toman(str(self.sp_fee.value()))
        return {
            "name": self.ed_name.text().strip(),
            "sessions_limit": int(self.sp_sessions.value()),
            "tuition_fee_toman": fee_toman,     # همیشه تومان
            "currency_unit_label": currency_label(),  # فقط برای نمایش در جدول
            "is_default": 1 if self.chk_default.isChecked() else 0
        }

class PricingProfileManager(QWidget):
    """
    مدیریت پروفایل‌های شهریه
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت پروفایل‌های شهریه")
        self.resize(700, 450)

        layout = QVBoxLayout(self)

        # جدول
        self.tbl = QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(["نام", "جلسات", "شهریه", "واحد", "پیش‌فرض"])
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # (اختیاری)
        self.tbl.setSelectionMode(QAbstractItemView.SingleSelection)

        layout.addWidget(self.tbl)

        # دکمه‌ها
        row_btns = QHBoxLayout()
        self.btn_add = QPushButton("➕ افزودن پروفایل")
        self.btn_edit = QPushButton("✏️ ویرایش")
        self.btn_delete = QPushButton("🗑️ حذف")
        self.btn_default = QPushButton("⭐ تنظیم به‌عنوان پیش‌فرض")

        for b in [self.btn_add, self.btn_edit, self.btn_delete, self.btn_default]:
            row_btns.addWidget(b)
        row_btns.addStretch(1)
        layout.addLayout(row_btns)

        # اتصال‌ها
        self.btn_add.clicked.connect(self.add_profile)
        self.btn_edit.clicked.connect(self.edit_profile)
        self.btn_delete.clicked.connect(self.delete_profile)
        self.btn_default.clicked.connect(self.make_default)

        self.reload()

    # --- Utilities ---
    def _selected_profile_row_id(self):
        row = self.tbl.currentRow()
        if row < 0:
            return None
        return self.tbl.item(row, 0).data(Qt.UserRole)  # id در ستون نام

    def reload(self):
        rows = list_pricing_profiles()
        # rows: (id, name, sessions_limit, tuition_fee, currency_unit, is_default)
        self.tbl.setRowCount(0)
        for (pid, name, sl, fee_toman, unit, is_def) in rows:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)

            # ستون نام (id در UserRole)
            it_name = QTableWidgetItem(name or "")
            it_name.setData(Qt.UserRole, pid)
            self.tbl.setItem(r, 0, it_name)

            # جلسات
            self.tbl.setItem(r, 1, QTableWidgetItem(str(sl)))

            # شهریه (نمایش فرمت‌شده + نگهداری مقدار تومان خام در UserRole)
            it_fee = QTableWidgetItem(format_currency_with_unit(fee_toman))
            it_fee.setData(Qt.UserRole, int(fee_toman))
            self.tbl.setItem(r, 2, it_fee)

            # واحد (صرفاً لیبل ذخیره‌شده یا لیبل فعلی)
            self.tbl.setItem(r, 3, QTableWidgetItem(unit or currency_label()))

            # پیش‌فرض
            self.tbl.setItem(r, 4, QTableWidgetItem("✓" if is_def else ""))

    # --- Actions ---
    def add_profile(self):
        dlg = PricingProfileDialog(mode='add', parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        vals = dlg.get_values()
        name = vals["name"]
        if not name:
            QMessageBox.warning(self, "خطا", "نام پروفایل را وارد کنید.")
            return
        try:
            create_pricing_profile(
                name=name,
                sessions=vals["sessions_limit"],
                fee=vals["tuition_fee_toman"],           # تومان
                currency_unit=vals["currency_unit_label"],  # برچسب برای نمایش
                is_default=bool(vals["is_default"])
            )
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ثبت پروفایل ممکن نشد:\n{e}")

    def edit_profile(self):
        pid = self._selected_profile_row_id()
        if not pid:
            QMessageBox.information(self, "انتخاب لازم", "لطفاً یک پروفایل را انتخاب کنید.")
            return

        # خواندن مقادیر فعلی از جدول
        row = self.tbl.currentRow()
        data = {
            "id": pid,
            "name": self.tbl.item(row, 0).text(),
            "sessions_limit": int(self.tbl.item(row, 1).text() or 0),
            # شهریهٔ خام تومان را از UserRole می‌خوانیم (نه از متنِ فرمت شده)
            "tuition_fee_toman": int(self.tbl.item(row, 2).data(Qt.UserRole) or 0),
            "is_default": 1 if self.tbl.item(row, 4).text().strip() == "✓" else 0
        }

        dlg = PricingProfileDialog(mode='edit', data=data, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        vals = dlg.get_values()
        if not vals["name"]:
            QMessageBox.warning(self, "خطا", "نام پروفایل را وارد کنید.")
            return

        # ویرایش در DB
        try:
            with get_connection() as conn:
                c = conn.cursor()
                if vals["is_default"]:
                    c.execute("UPDATE pricing_profiles SET is_default=0")
                c.execute("""
                    UPDATE pricing_profiles
                       SET name=?, sessions_limit=?, tuition_fee=?, currency_unit=?, is_default=?
                     WHERE id=?
                """, (vals["name"], vals["sessions_limit"], vals["tuition_fee_toman"],
                      vals["currency_unit_label"], vals["is_default"], pid))
                conn.commit()
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"ذخیره تغییرات ممکن نشد:\n{e}")

    def delete_profile(self):
        pid = self._selected_profile_row_id()
        if not pid:
            QMessageBox.information(self, "انتخاب لازم", "لطفاً یک پروفایل را انتخاب کنید.")
            return

        # چک استفاده شدن در student_terms
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM student_terms WHERE profile_id=?", (pid,))
            in_use = c.fetchone()[0] > 0

        if in_use:
            QMessageBox.warning(self, "امکان حذف نیست",
                                "این پروفایل در ترم‌های ثبت‌شده استفاده شده است و قابل حذف نیست.")
            return

        if QMessageBox.question(self, "حذف پروفایل",
                                "آیا از حذف این پروفایل مطمئن هستید؟",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            with get_connection() as conn:
                conn.execute("DELETE FROM pricing_profiles WHERE id=?", (pid,))
                conn.commit()
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"حذف پروفایل ممکن نشد:\n{e}")

    def make_default(self):
        pid = self._selected_profile_row_id()
        if not pid:
            QMessageBox.information(self, "انتخاب لازم", "لطفاً یک پروفایل را انتخاب کنید.")
            return

        try:
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE pricing_profiles SET is_default=0")
                c.execute("UPDATE pricing_profiles SET is_default=1 WHERE id=?", (pid,))
                conn.commit()
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"تنظیم پیش‌فرض ممکن نشد:\n{e}")