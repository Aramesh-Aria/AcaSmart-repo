import sqlite3
from PySide6.QtWidgets import QMainWindow, QWidget, QFormLayout, QLineEdit, QPushButton, QMessageBox
from dashboard_window import DashboardWindow
from utils import hash_password
from db_helper import get_connection

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Login")
        self.setGeometry(400, 50, 350, 150)

        # Apply theme-based icon
        try:
            from theme_manager import apply_theme_icon
            apply_theme_icon(self)
        except Exception as e:
            print(f"⚠️ Could not apply theme icon to login window: {e}")

        central_widget = QWidget()
        form_layout = QFormLayout()

        self.input_mobile = QLineEdit()
        form_layout.addRow("Username:", self.input_mobile)

        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Password:", self.input_password)

        self.btn_login = QPushButton("Login")
        self.btn_login.clicked.connect(self.handle_login)
        form_layout.addRow(self.btn_login)

        self.input_password.returnPressed.connect(self.btn_login.click)
        self.input_mobile.returnPressed.connect(self.input_password.setFocus)

        central_widget.setLayout(form_layout)
        self.setCentralWidget(central_widget)

    def handle_login(self):
        mobile = self.input_mobile.text().strip()
        password = self.input_password.text()
        hashed_input = hash_password(password)

        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT * FROM users WHERE mobile=? AND password=?",
            (mobile, hashed_input)
        )
        user = c.fetchone()
        conn.close()

        if user:
            self.dashboard = DashboardWindow(logged_in_mobile=mobile)
            self.dashboard.show()
            self.close()
        else:
            QMessageBox.warning(self, "Login Failed", "Incorrect username or password.")
