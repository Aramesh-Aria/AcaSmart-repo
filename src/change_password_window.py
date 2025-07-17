from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton, QMessageBox
from utils import hash_password
from db_helper import get_connection

class ChangeCredentialsWindow(QWidget):
    def __init__(self, logged_in_mobile):
        super().__init__()
        self.setWindowTitle("تغییر اطلاعات ورود")
        self.setGeometry(300, 300, 350, 200)
        self.logged_in_mobile = logged_in_mobile

        form_layout = QFormLayout()

        self.input_new_mobile = QLineEdit()
        form_layout.addRow(": نام کاربری جدید (اختیاری)", self.input_new_mobile)

        self.input_current_password = QLineEdit()
        self.input_current_password.setEchoMode(QLineEdit.Password)
        form_layout.addRow(": رمز فعلی", self.input_current_password)

        self.input_new_password = QLineEdit()
        self.input_new_password.setEchoMode(QLineEdit.Password)
        form_layout.addRow(": رمز جدید", self.input_new_password)

        self.input_confirm_password = QLineEdit()
        self.input_confirm_password.setEchoMode(QLineEdit.Password)
        form_layout.addRow(": تکرار رمز جدید", self.input_confirm_password)

        self.btn_submit = QPushButton("ثبت تغییرات")
        self.btn_submit.clicked.connect(self.update_credentials)
        form_layout.addRow(self.btn_submit)

        self.setLayout(form_layout)

    def update_credentials(self):
        current_pass = self.input_current_password.text().strip()
        new_pass = self.input_new_password.text().strip()
        confirm_pass = self.input_confirm_password.text().strip()
        new_mobile = self.input_new_mobile.text().strip()

        if not current_pass:
            QMessageBox.warning(self, "خطا", "لطفاً رمز فعلی را وارد کنید.")
            return

        change_mobile = bool(new_mobile)
        change_password = bool(new_pass or confirm_pass)

        if not change_mobile and not change_password:
            QMessageBox.warning(self, "خطا", "لطفاً حداقل یکی از فیلدهای رمز جدید یا نام کاربری جدید را وارد کنید.")
            return

        if (new_pass and not confirm_pass) or (confirm_pass and not new_pass):
            QMessageBox.warning(self, "خطا", "لطفاً رمز جدید و تکرار آن را کامل وارد کنید.")
            return

        if new_pass != confirm_pass:
            QMessageBox.warning(self, "خطا", "رمز جدید و تکرار آن مطابقت ندارند.")
            return

        conn = get_connection()
        c = conn.cursor()

        c.execute("SELECT password FROM users WHERE mobile=?", (self.logged_in_mobile,))
        row = c.fetchone()

        if not row or row[0] != hash_password(current_pass):
            QMessageBox.warning(self, "خطا", "رمز فعلی نادرست است.")
            conn.close()
            return

        c.execute("DELETE FROM users")

        final_mobile = new_mobile if change_mobile else self.logged_in_mobile
        final_password = hash_password(new_pass) if change_password else row[0]

        c.execute("INSERT INTO users (mobile, password) VALUES (?, ?)", (final_mobile, final_password))
        conn.commit()
        conn.close()

        QMessageBox.information(self, "موفق", "اطلاعات ورود با موفقیت تغییر کرد.")
        self.close()
