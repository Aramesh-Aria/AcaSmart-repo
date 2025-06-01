from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from financial_report_window import FinancialReportWindow
from attendance_report_window import AttendanceReportWindow
from student_term_summary_window import StudentTermSummaryWindow
from contacts_window import ContactsWindow
from teacher_summary_window import TeacherSummaryWindow

class ReportsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("گزارش‌ها")
        self.setGeometry(200, 200, 400, 400)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        button_style = "font-size: 15px; padding: 10px;"

        reports = [
            ("💵 گزارش مالی هنرجویان", self.open_financial_report),
            ("📋 گزارش حضور و غیاب", self.open_attendance_report),
            ("🏫🎓 گزارش هنرجویان", self.open_student_report),
            ("گزارش اساتید", self.open_teacher_report),
            ("📒 دفترچه تلفن", self.open_student_contacts),
        ]

        for title, handler in reports:
            btn = QPushButton(title)
            btn.setStyleSheet(button_style)
            btn.clicked.connect(handler)
            layout.addWidget(btn)

        self.setLayout(layout)

    def open_financial_report(self):
        self.financial_window = FinancialReportWindow()
        self.financial_window.show()

    def open_attendance_report(self):
        self.attendance_report_window = AttendanceReportWindow()
        self.attendance_report_window.show()

    def open_student_report(self):
        self.student_term_summary_report_window = StudentTermSummaryWindow()
        self.student_term_summary_report_window.show()

    def open_student_contacts(self):
        self.contacts_window = ContactsWindow()
        self.contacts_window.show()

    def open_teacher_report(self):
        self.teachers_summary_report_window = TeacherSummaryWindow()
        self.teachers_summary_report_window.show()