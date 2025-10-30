from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from acasmart.ui.widgets.theme_manager import ThemeManager

class ReportsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("گزارش‌ها")
        self.setGeometry(200, 200, 400, 400)

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # title = QLabel("📊 گزارش‌ها")
        # title.setAlignment(Qt.AlignRight)
        # title.setProperty("sectionTitle", True)
        # layout.addWidget(title)

        reports = [
            ("💵 گزارش مالی هنرجویان", self.open_financial_report),
            ("📋 گزارش حضور و غیاب", self.open_attendance_report),
            ("🏫🎓 گزارش هنرجویان", self.open_student_report),
            ("گزارش اساتید", self.open_teacher_report),
            ("📒 دفترچه تلفن", self.open_student_contacts),
        ]

        for caption, handler in reports:
            btn = QPushButton(caption)
            btn.setProperty("variant", "secondary")
            btn.clicked.connect(handler)
            layout.addWidget(btn)
            try:
                ThemeManager.repolish(btn)
            except Exception:
                pass

        self.setLayout(layout)
        try:
            ThemeManager.repolish(title)
        except Exception:
            pass

    def open_financial_report(self):
        from acasmart.ui.reports.financial_report_window import FinancialReportWindow
        self.financial_window = FinancialReportWindow()
        self.financial_window.show()

    def open_attendance_report(self):    
        from acasmart.ui.reports.attendance_report_window import AttendanceReportWindow
        self.attendance_report_window = AttendanceReportWindow()
        self.attendance_report_window.show()

    def open_student_report(self):
        from acasmart.ui.reports.student_term_summary_window import StudentTermSummaryWindow
        self.student_term_summary_report_window = StudentTermSummaryWindow()
        self.student_term_summary_report_window.show()

    def open_student_contacts(self):
        from acasmart.ui.reports.contacts_window import ContactsWindow
        self.contacts_window = ContactsWindow()
        self.contacts_window.show()

    def open_teacher_report(self):
        from acasmart.ui.reports.teacher_summary_window import TeacherSummaryWindow
        self.teachers_summary_report_window = TeacherSummaryWindow()
        self.teachers_summary_report_window.show()
