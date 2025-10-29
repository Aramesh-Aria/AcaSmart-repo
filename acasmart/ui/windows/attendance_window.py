from acasmart.data.repos.attendance_repo import count_attendance, fetch_attendance_by_date, insert_attendance_with_date, count_attendance_by_term, delete_attendance
from acasmart.data.repos.settings_repo import get_setting, get_setting_bool
from acasmart.data.repos.terms_repo import get_student_term, recalc_term_end_by_id, get_term_dates
from acasmart.data.repos.sessions_repo import (
    delete_future_sessions,
    delete_sessions_for_expired_terms,
    fetch_students_sessions_for_class_on_date,
)
from acasmart.data.repos.classes_repo import fetch_classes_on_weekday
from acasmart.data.repos.notifications_repo import has_renew_sms_been_sent, mark_renew_sms_sent
from acasmart.data.repos.reports_repo import get_class_and_teacher_name
from acasmart.data.repos.profiles_repo import get_term_config
from acasmart.data.repos.attendance_repo import count_present_attendance_for_term
from acasmart.data.repos.students_repo import get_student_contact
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox, QDialog
)
from PySide6.QtCore import Qt
import functools
import sqlite3

from acasmart.ui.widgets.shamsi_date_popup import ShamsiDatePopup
import jdatetime
from acasmart.services.sms_notifier import SmsNotifier, SmsStatus

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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "نام هنرجو", "ساعت", "حاضر", "غائب", "term_id", "عملیات"])
        self.table.setColumnHidden(0, True)
        self.table.setColumnHidden(5, True)
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
        """بارگذاری لیست حضور/غیاب با سقفِ per-term و شمارش کل جلسات (حاضر+غایب)."""
        if self.selected_class_id is None:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا یک کلاس را انتخاب کنید.")
            return

        if not self.selected_shamsi_date:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا تاریخ جلسه (شمسی) را انتخاب کنید.")
            return

        selected_date = self.selected_shamsi_date
        self.table.setRowCount(0)

        for sid, name, teacher, session_time, term_id in fetch_students_sessions_for_class_on_date(self.selected_class_id, selected_date):
            # تنظیمات همان ترم
            cfg = get_term_config(term_id)  # dict: {"sessions_limit": ... , ...}
            term_limit = int(cfg.get("sessions_limit") or 12)
            notify_session_number = max(0, term_limit - 1)

            # شمارش کل ثبت‌ها برای همان ترم (حاضر + غایب)
            done_total = count_attendance_by_term(sid, self.selected_class_id, term_id)

            # رکورد امروز (None/True/False)
            record = fetch_attendance_by_date(sid, self.selected_class_id, selected_date, term_id)

            row = self.table.rowCount()
            self.table.insertRow(row)

            # ستون مخفی: student_id
            id_item = QTableWidgetItem(str(sid))
            id_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 0, id_item)

            # ستون مخفی: term_id
            term_item = QTableWidgetItem(str(term_id))
            term_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 5, term_item)

            # نام + وضعیت SMS
            display_name = name
            name_item = QTableWidgetItem()
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            name_item.setToolTip(f"جلسات ثبت‌شده (کل): {done_total} از {term_limit} — باقی‌مانده: {max(0, term_limit - done_total)}")

            # وضعیت SMS برای نمایش آیکون/ایموجی کنار نام و tooltip
            sent_flag = has_renew_sms_been_sent(sid, term_id)
            sms_enabled = get_setting_bool("sms_enabled", True)
            if sent_flag:
                display_name += "  ✅"
                name_item.setToolTip(name_item.toolTip() + "\nپیامک با موفقیت ارسال شد")
            else:
                if not sms_enabled:
                    display_name += "  ⚠️"
                    name_item.setToolTip(name_item.toolTip() + "\nارسال پیامک غیرفعال است")
                elif done_total >= notify_session_number:
                    display_name += "  ❌"
                    name_item.setToolTip(name_item.toolTip() + "\nارسال پیامک ناموفق/در انتظار")

            name_item.setText(display_name)
            self.table.setItem(row, 1, name_item)

            # ساعت جلسه
            time_item = QTableWidgetItem(session_time)
            time_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(row, 2, time_item)

            # چک‌باکس‌ها
            present_chk = QCheckBox()
            absent_chk = QCheckBox()

            # اگر ترم پر شده و امروز هنوز چیزی ثبت نشده، اجازه ثبت نده
            if done_total >= term_limit and record is None:
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

            self.table.setCellWidget(row, 3, present_chk)
            self.table.setCellWidget(row, 4, absent_chk)
            self.table.setRowHeight(row, 25)

            # دکمه حذف رکورد امروز
            btn_delete = QPushButton("❌ حذف")
            btn_delete.setToolTip("حذف حضور/غیاب ثبت‌شده در این تاریخ")
            # اگر رکوردی برای این روز ثبت نشده، دکمه را غیرفعال کن
            btn_delete.setEnabled(record is not None)

            btn_delete.clicked.connect(
                functools.partial(
                    self.delete_attendance_row,
                    sid,
                    self.selected_class_id,
                    term_id,
                    selected_date
                )
            )

            op_layout = QHBoxLayout()
            op_layout.addWidget(btn_delete)
            op_layout.setContentsMargins(0, 0, 0, 0)
            op_layout.setAlignment(Qt.AlignCenter)

            op_widget = QWidget()
            op_widget.setLayout(op_layout)
            self.table.setCellWidget(row, 6, op_widget)


    def _on_present_changed(self, other_chk, state):
        if state == Qt.Checked:
            other_chk.setChecked(False)

    def _on_absent_changed(self, other_chk, state):
        if state == Qt.Checked:
            other_chk.setChecked(False)

    def save_attendance(self):
        """ذخیره حضور/غیاب؛ SMS وقتی ۱ جلسه باقی مانده؛ حذف جلسات آینده پس از ست‌شدن end_date."""
        if not self.selected_shamsi_date:
            QMessageBox.warning(self, "خطا", "لطفاً ابتدا تاریخ جلسه (شمسی) را انتخاب کنید.")
            return

        selected_date = self.selected_shamsi_date
        if self.selected_class_id is None:
            QMessageBox.warning(self, "خطا", "ابتدا کلاس را انتخاب کنید.")
            return

        failed_sms = []

        for row in range(self.table.rowCount()):
            sid = int(self.table.item(row, 0).text())
            present_chk = self.table.cellWidget(row, 3)
            absent_chk  = self.table.cellWidget(row, 4)
            present = present_chk.isChecked() if present_chk else False
            absent  = absent_chk.isChecked()  if absent_chk  else False

            try:
                term_id_item = self.table.item(row, 5)
                if term_id_item is None:
                    continue
                term_id = int(term_id_item.text())

                # بازه ترم
                term_dates = get_term_dates(term_id)  # (start_date, end_date)
                if not term_dates:
                    continue
                start_date, end_date = term_dates

                # بیرون از بازه ترم ثبت نکن
                if selected_date < start_date or (end_date and selected_date > end_date):
                    continue

                # سقفِ همان ترم
                cfg = get_term_config(term_id)
                term_limit = int(cfg.get("sessions_limit") or 12)
                notify_session_number = max(0, term_limit - 1)

                # فقط اگر یکی از چک‌باکس‌ها زده شده باشد ثبت کن
                if present or absent:
                    is_present = 1 if present else 0

                    # --- ثبت واقعی رکورد امروز ---
                    ended = insert_attendance_with_date(
                        sid, self.selected_class_id, term_id, selected_date, is_present
                    )

                    # شمارش بعد از ثبت (کل: حاضر+غایب)
                    total_after = count_attendance_by_term(sid, self.selected_class_id, term_id)

                    # لاگ کمکی
                    print(f"[DEBUG] sid={sid} term_id={term_id} total_after={total_after} limit={term_limit} notify={notify_session_number} ended={ended}")

                    # اگر حالا «دقیقاً یک جلسه مانده» → SMS (و نه جلسه بعدی)
                    if (total_after == notify_session_number) and (not has_renew_sms_been_sent(sid, term_id)):
                        name, phone = get_student_contact(sid)
                        if phone:
                            class_name, _ = get_class_and_teacher_name(self.selected_class_id)

                            try:
                                # send sms
                                result = self.notifier.send_renew_term_notification(name, phone, class_name)
                                # اگر ارسال غیرفعال بود، فلگ ارسال را نزن
                                if isinstance(result, dict) and result.get("status") == SmsStatus.DISABLED:
                                    print(f"[INFO] SMS disabled for sid={sid}, term_id={term_id}")
                                else:
                                    # flag as send
                                    mark_renew_sms_sent(sid, term_id)
                                print(f"[INFO] SMS sent for sid={sid}, term_id={term_id}")
                            except Exception as e:
                                print(f"[ERROR] SMS failed for sid={sid}: {e}")
                                failed_sms.append(name)

                    # اگر با همین ثبت، ترم بسته شد → جلسات آینده را حذف کن
                    if ended:
                        try:
                            # ترجیحاً با end_date جدید پاک کن
                            _start, _end = get_term_dates(term_id)
                            cutoff = _end or selected_date
                            delete_future_sessions(sid, self.selected_class_id, cutoff)
                        except sqlite3.Error as e:
                            QMessageBox.warning(self, "خطا", f"حذف جلسات باقی‌مانده با خطا مواجه شد: {e}")

            except sqlite3.IntegrityError as e:
                QMessageBox.warning(self, "خطا", f"خطا در ذخیره‌سازی: {e}")

        if failed_sms:
            QMessageBox.warning(self, "خطای پیامک", "ارسال پیام برای هنرجویان زیر انجام نشد:\n" + "\n".join(failed_sms))
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


    def delete_attendance_row(self, student_id: int, class_id: int, term_id: int, date_value: str):
        """حذف حضور/غیابِ همان روز و بازخوانی جدول؛ سپس بازمحاسبهٔ پایان ترم."""
        try:
            # حذف بر اساس ستون date
            deleted = delete_attendance(student_id, class_id, term_id, date_value)

            # اگر با حذف، مجموع از limit کمتر شد و end_date قبلاً ست بود → بازش کن
            try:
                recalc_term_end_by_id(term_id)
            except Exception:
                pass

            if deleted == 0:
                print(f"[WARN] No attendance row deleted for ({student_id}, {class_id}, {term_id}, {date_value})")

            self.load_attendance()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"حذف حضور/غیاب با خطا مواجه شد:\n{e}")