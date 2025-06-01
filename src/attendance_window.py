from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox,QDialog
)
import functools
from PyQt5.QtCore import Qt
import sqlite3

from db_helper import (fetch_students_with_teachers_for_class,
                       get_student_term,fetch_attendance_by_date,count_attendance,get_setting,
            delete_future_sessions,delete_sessions_for_expired_terms,
            fetch_classes_on_weekday,insert_attendance_with_date,get_term_id_by_student_class_and_date,get_term_dates,
            get_student_contact,get_class_and_teacher_name,has_renew_sms_been_sent, mark_renew_sms_sent
)
from shamsi_date_popup import ShamsiDatePopup
import jdatetime
from sms_notifier import SmsNotifier

class AttendanceManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("مدیریت حضور و غیاب")
        self.setGeometry(300, 200, 600, 500)

        self.last_selected_date = jdatetime.date.today().isoformat()  # "1403-02-31"

        self.notifier = SmsNotifier()
        # پاک‌سازی خودکار جلسات برای ترم‌های منقضی
        try:
            delete_sessions_for_expired_terms()
        except sqlite3.Error as e:
            print(f"Error clearing expired sessions: {e}")


        layout = QVBoxLayout()


        # --------- انتخاب تاریخ ----------
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel(": تاریخ جلسه"))
        self.selected_shamsi_date = None
        self.date_btn = QPushButton("📅 انتخاب تاریخ جلسه")
        self.date_btn.clicked.connect(self.open_date_picker)
        date_layout.addWidget(self.date_btn)
        layout.addLayout(date_layout)

        # --------- انتخاب کلاس (غیرفعال تا قبل از انتخاب تاریخ) ----------
        class_layout = QHBoxLayout()
        class_layout.addWidget(QLabel(": انتخاب کلاس"))
        self.combo_class = QComboBox()
        self.combo_class.setEnabled(False)
        self.combo_class.currentIndexChanged.connect(self.on_class_changed)
        class_layout.addWidget(self.combo_class)
        layout.addLayout(class_layout)

        # --------- جدول حضور ----------
        # جدول حضور: ID مخفی، نام هنرجو، چک‌باکس حاضر، چک‌باکس غائب
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "نام هنرجو", "حاضر", "غائب"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # --------- دکمه ذخیره ----------
        self.btn_save = QPushButton("ذخیره حضور و غیاب ➕")
        self.btn_save.clicked.connect(self.save_attendance)
        layout.addWidget(self.btn_save)

        self.setLayout(layout)

        self.showMaximized()

        # مقداردهی اولیه بر اساس تاریخ آخر استفاده‌شده
        self.selected_shamsi_date = self.last_selected_date
        self.date_btn.setText(f"📅 {self.selected_shamsi_date}")
        self.load_classes()

    def load_classes(self):
        """Populate the class combobox based on selected date"""
        self.combo_class.clear()
        weekday_map = {
            0: "دوشنبه",
            1: "سه‌شنبه",
            2: "چهارشنبه",
            3: "پنجشنبه",
            4: "جمعه",
            5: "شنبه",
            6: "یکشنبه",
        }

        if not self.selected_shamsi_date:
            return

        # محاسبه دقیق روز هفته با تبدیل به میلادی
        jdate_obj = jdatetime.date.fromisoformat(self.selected_shamsi_date)
        gregorian = jdate_obj.togregorian()
        weekday = gregorian.weekday()  # Monday = 0
        current_day = weekday_map[weekday]

        # واکشی کلاس‌هایی که در این روز برگزار می‌شوند
        classes = fetch_classes_on_weekday(current_day)

        if not classes:
            QMessageBox.information(
                self,
                "هیچ کلاسی یافت نشد",
                f"در روز {current_day} ({self.selected_shamsi_date}) کلاسی یافت نشد.",
            )
            self.combo_class.setEnabled(False)
            return

        for cid, name, teacher, instr, cls_day, start, end, room in classes:
            self.combo_class.addItem(f"{name} — {start}", cid)

        self.combo_class.setEnabled(True)
        self.combo_class.setCurrentIndex(0)

    def on_class_changed(self, idx):
        """تنظیم کلاس انتخاب‌شده و بارگذاری حضور آن."""
        self.selected_class_id = self.combo_class.itemData(idx)
        # فقط زمانی فراخوانی کن که کلاس واقعاً انتخاب شده
        if self.selected_class_id is not None:
            self.load_attendance()

    def load_attendance(self):
        """بارگذاری دانشجویان دارای ترم فعال برای کلاس انتخاب‌شده و تاریخ مشخص‌شده."""
        if self.selected_class_id is None:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا یک کلاس را انتخاب کنید.")
            return

        if not self.selected_shamsi_date:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا تاریخ جلسه (شمسی) را انتخاب کنید.")
            return

        selected_date = self.selected_shamsi_date
        self.table.setRowCount(0)
        limit = int(get_setting("term_session_count", 12))

        for sid, name, teacher in fetch_students_with_teachers_for_class(self.selected_class_id):
            term_id = get_term_id_by_student_class_and_date(sid, self.selected_class_id, selected_date)
            if not term_id:
                continue

            done = count_attendance(sid, self.selected_class_id)

            row = self.table.rowCount()
            self.table.insertRow(row)

            # ستون مخفی ID
            id_item = QTableWidgetItem(str(sid))
            id_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, id_item)

            # بررسی ثبت پیام برای این ترم
            notified = False
            try:
                with sqlite3.connect("academy.db") as conn:
                    c = conn.cursor()
                    c.execute("""
                        SELECT 1 FROM notified_terms
                        WHERE term_id = ? AND student_id = ? AND class_id = ?
                    """, (term_id, sid, self.selected_class_id))
                    notified = c.fetchone() is not None
            except Exception as e:
                print(f"⚠️ خطا در بررسی وضعیت ارسال پیام: {e}")

            # ستون نام هنرجو + وضعیت پیامک
            display_name = name + " ✅" if notified else name
            name_item = QTableWidgetItem(display_name)
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            name_item.setToolTip(f"جلسات ثبت‌شده: {done} از {limit}")
            if has_renew_sms_been_sent(sid, term_id):
                name_item.setForeground(Qt.green)
                name_item.setText(f"{name}  ✅")
            self.table.setItem(row, 1, name_item)

            # چک‌باکس‌ها (حاضر / غایب)
            record = fetch_attendance_by_date(sid, self.selected_class_id, selected_date, term_id)
            present_chk = QCheckBox()
            absent_chk = QCheckBox()

            if done >= limit:
                present_chk.setEnabled(False)
                absent_chk.setEnabled(False)

            present_chk.stateChanged.connect(
                functools.partial(self._on_present_changed, absent_chk)
            )
            absent_chk.stateChanged.connect(
                functools.partial(self._on_absent_changed, present_chk)
            )

            if record is True:
                present_chk.setChecked(True)
            elif record is False:
                absent_chk.setChecked(True)

            self.table.setCellWidget(row, 2, present_chk)
            self.table.setCellWidget(row, 3, absent_chk)
            self.table.setRowHeight(row, 25)

    def _on_present_changed(self, other_chk, state):
        if state == Qt.Checked:
            other_chk.setChecked(False)

    def _on_absent_changed(self, other_chk, state):
        if state == Qt.Checked:
            other_chk.setChecked(False)

    def save_attendance(self):
        """ذخیره تغییرات حضور، و حذف جلسات آینده پس از پایان ترم."""
        if not self.selected_shamsi_date:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا تاریخ جلسه (شمسی) را انتخاب کنید.")
            return

        selected_date = self.selected_shamsi_date
        if self.selected_class_id is None:
            QMessageBox.warning(self, "خطا", "ابتدا کلاس را انتخاب کنید.")
            return

        limit = int(get_setting("term_session_count", 12))
        notify_session_number = limit - 1
        failed_sms = []

        for row in range(self.table.rowCount()):
            sid = int(self.table.item(row, 0).text())
            present = self.table.cellWidget(row, 2).isChecked()
            absent = self.table.cellWidget(row, 3).isChecked()

            try:
                term_id = get_term_id_by_student_class_and_date(sid, self.selected_class_id, selected_date)
                if not term_id:
                    continue

                term = get_term_dates(term_id)
                if not term:
                    continue
                start_date, end_date = term
                if selected_date < start_date or (end_date and selected_date > end_date):
                    continue

                if present or absent:
                    is_present = 1 if present else 0
                    insert_attendance_with_date(sid, self.selected_class_id, term_id, selected_date, is_present)
                    total = count_attendance(sid, self.selected_class_id)

                    if total == notify_session_number and not has_renew_sms_been_sent(sid, term_id):
                        name, phone = get_student_contact(sid)
                        if phone:
                            class_name, _ = get_class_and_teacher_name(self.selected_class_id)
                            try:
                                self.notifier.send_renew_term_notification(name, phone, class_name)
                                mark_renew_sms_sent(sid, term_id)
                            except Exception as e:
                                print(f"❌ خطا در ارسال پیامک به {name}: {e}")
                                failed_sms.append(name)

            except sqlite3.IntegrityError as e:
                QMessageBox.warning(self, "خطا", f"خطا در ذخیره‌سازی: {e}")

            term = get_student_term(sid, self.selected_class_id)
            if term and term[1] is not None and count_attendance(sid, self.selected_class_id) >= limit:
                try:
                    delete_future_sessions(sid, self.selected_class_id, term[1])
                except sqlite3.Error as e:
                    QMessageBox.warning(self, "خطا", f"حذف جلسات باقی‌مانده با خطا مواجه شد: {e}")

        if failed_sms:
            QMessageBox.warning(
                self,
                "خطای پیامک",
                "ارسال پیام برای هنرجویان زیر انجام نشد:\n" + "\n".join(failed_sms)
            )
        else:
            QMessageBox.information(self, "موفق", "حضور و غیاب با موفقیت ذخیره شد.")

        self.load_attendance()

    def open_date_picker(self):
        dlg = ShamsiDatePopup(initial_date=self.selected_shamsi_date)
        if dlg.exec_() == QDialog.Accepted:
            shamsi_date = dlg.get_selected_date()
            self.selected_shamsi_date = shamsi_date
            self.date_btn.setText(f"📅 {shamsi_date}")
            self.last_selected_date = shamsi_date  # چون string شمسی هست
            self.load_classes()

