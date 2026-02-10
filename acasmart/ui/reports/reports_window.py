from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from acasmart.ui.widgets.theme_manager import ThemeManager
from acasmart.ui.widgets.base_secondary_window import BaseSecondaryWindow

class ReportsWindow(BaseSecondaryWindow):
    def __init__(self, return_target: QWidget | None = None):
        super().__init__("گزارش‌ها", return_target)
        self.setGeometry(200, 200, 400, 400)

        layout = self.content_layout()
        layout.setSpacing(12)

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

    def open_financial_report(self):
        from acasmart.ui.reports.financial_report_window import FinancialReportWindow
        self.financial_window = FinancialReportWindow(return_target=self)
        self.financial_window.show()

    def open_attendance_report(self):    
        from acasmart.ui.reports.attendance_report_window import AttendanceReportWindow
        self.attendance_report_window = AttendanceReportWindow(return_target=self)
        self.attendance_report_window.show()

    def open_student_report(self):
        from acasmart.ui.reports.student_term_summary_window import StudentTermSummaryWindow
        self.student_term_summary_report_window = StudentTermSummaryWindow(return_target=self)
        self.student_term_summary_report_window.show()

    def open_student_contacts(self):
        from acasmart.ui.reports.contacts_window import ContactsWindow
        self.contacts_window = ContactsWindow(return_target=self)
        self.contacts_window.show()

    def open_teacher_report(self):
        from acasmart.ui.reports.teacher_summary_window import TeacherSummaryWindow
        self.teachers_summary_report_window = TeacherSummaryWindow(return_target=self)
        self.teachers_summary_report_window.show()
