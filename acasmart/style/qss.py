BASE_QSS = """
* { font-family: %(font)s; }
QWidget        { background: %(bg)s; color: %(text)s; }
QFrame#Card    { background: %(surface)s; border: 1px solid %(border)s; border-radius: %(radius)s; }
QGroupBox      { border: 1px solid %(border)s; border-radius: %(radius)s; margin-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: %(muted)s; }

/* QpushButton*/
QPushButton {
  background: %(primary)s; color: %(onPrimary)s;
  border: none; border-radius: %(radius)s; padding: 6px 12px;
}

QPushButton[variant="primary"]:hover   { background: %(primaryHover)s; }
QPushButton[variant="primary"]:pressed { background: %(primaryActive)s; }

QPushButton:disabled { background: %(border)s; color: %(muted)s; }


QToolButton { border-radius: %(radius)s; padding: 6px 8px; }
QToolButton:hover { background: %(rowHover)s; }

QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit {
  background: %(surface)s; color: %(text)s;
  border: 1px solid %(border)s; border-radius: %(radius)s; padding: 6px 10px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QTextEdit:focus {
  border: 1px solid %(primary)s;
}

QHeaderView::section {
  background: %(surface)s; color: %(text)s; border: 0; border-bottom: 1px solid %(border)s; padding: 8px;
}
QTableView {
  gridline-color: %(border)s;
  selection-background-color: %(primary)s;
  selection-color: %(onPrimary)s;
  alternate-background-color: %(rowHover)s;
}
QTableView::item:hover { background: %(rowHover)s; }
QScrollBar:vertical   { background: transparent; width: 12px; }
QScrollBar::handle:vertical { background: %(border)s; border-radius: 6px; }
QToolTip {
  background: %(surface)s; color: %(text)s; border: 1px solid %(border)s; padding: 6px;
}
/* Buttons with variants */
QPushButton[variant="primary"]  {
  background: %(primary)s;
  color: %(onPrimary)s;
  border: none;
  border-radius: %(radius)s;
  padding: 6px 12px;
}
QPushButton[variant="primary"]:hover {
  background: %(primaryHover)s;
}
QPushButton[variant="primary"]:pressed {
  background: %(primaryActive)s;
}
/* 👇 این مهمه */
QPushButton[variant="primary"]:disabled {
  background: %(border)s;
  color: %(muted)s;
}

/* secondary */
QPushButton[variant="secondary"] {
  background: %(surface)s;
  color: %(text)s;
  border: 1px solid %(border)s;
  border-radius: %(radius)s;
  padding: 6px 12px;
}
QPushButton[variant="secondary"]:hover {
  background: %(rowHover)s;
}
QPushButton[variant="secondary"]:disabled {
  background: %(surface)s;
  color: %(muted)s;
  border: 1px solid %(border)s;
}

/* ghost */
QPushButton[variant="ghost"] {
  background: transparent;
  color: %(text)s;
  border: none;
  padding: 6px 12px;
}
QPushButton[variant="ghost"]:hover {
  background: rgba(0, 0, 0, 0.04); /* ملایم‌تر از rowHover */
}
QPushButton[variant="ghost"]:disabled {
  color: %(muted)s;
  background: transparent;
  opacity: 0.6;
}


/* Badge statuses */
QLabel#Badge {
  padding: 2px 8px; border-radius: 999px; color: white; font-weight: 600;
}
QLabel#Badge[status="success"] { background: %(success)s; }
QLabel#Badge[status="warning"] { background: %(warning)s; color: black; }
QLabel#Badge[status="error"]   { background: %(error)s; }
QLabel#Badge[status="info"]    { background: %(primary)s; }
QLabel#MutedCaption { color: %(muted)s; font-size: 12px; }

/* Tables */
QTableView {
  gridline-color: %(border)s;
  selection-background-color: %(primary)s;
  selection-color: %(onPrimary)s;
  alternate-background-color: %(rowHover)s;
}

/* Cards */
QFrame#Card { background: %(surface)s; border: 1px solid %(border)s; border-radius: %(radius)s; }

/* Toolbar */
QToolBar#GlobalToolbar {
  background: %(surface)s;
  border-bottom: 1px solid %(border)s;
  spacing: 6px;
}
QToolBar#GlobalToolbar QToolButton {
  background: transparent;
  border-radius: %(radius)s;
  padding: 6px 8px;
}
QToolBar#GlobalToolbar QToolButton:hover {
  background: %(rowHover)s;   /* هاور تولبار */
}

/* Menu popup */
QMenu {
  background: %(surface)s;
  color: %(text)s;
  border: 1px solid %(border)s;
  padding: 4px;
}
QMenu::item {
  padding: 6px 12px;
  border-radius: %(radius)s;
}
QMenu::item:selected {
  background: %(rowHover)s;   /* هاور آیتم‌های منو */
  color: %(text)s;
}
QMenu::separator {
  height: 1px;
  background: %(border)s;
  margin: 4px 8px;
}

/* ----- List Widgets ----- */
QListWidget {
  background: %(surface)s;
  border: 1px solid %(border)s;
  border-radius: %(radius)s;
}

QListWidget::item {
  padding: 6px 10px;
  border-radius: %(radius)s;
  color: %(text)s;
}

/* لیست هنرجو – انتخاب‌شده */
QListWidget#StudentList::item:selected {
  background: %(primaryLight)s;
  color: %(text)s;          /* نه onPrimary – که خوانا بمونه */
  font-weight: 600;
}
QListWidget::item:selected {
  background: %(primaryLight)s;
  color: %(text)s;       
}

QListWidget::item:hover {
  background: %(rowHover)s;
}

/* Specific tweaks for Class & Student lists */
QListWidget#StudentList, QListWidget#ClassList2 {
  margin-bottom: 6px;
}


/* لیست کلاس – انتخاب‌شده */
QListWidget#ClassList {
    background: transparent;
    border: none;
}

QListWidget#ClassList::item {
    background: transparent;
    border: none;
    padding: 0;
    margin: 6px 0;
}

QListWidget#ClassList::item:selected,
QListWidget#ClassList::item:selected,
QListWidget#ClassList::item:hover,
QListWidget#ClassList::item:selected:active,
QListWidget#ClassList::item:selected:!active {
    background: transparent;
}


/* هاور عمومی */
QListWidget::item:hover {
  background: %(rowHover)s;
}

QTableWidget#AttendanceTable::item {
  padding: 4px 6px;
}
QTableWidget#AttendanceTable QCheckBox {
  margin-left: auto;
  margin-right: auto;
}

/* ----- Section Titles ----- */
QLabel[sectionTitle="true"] {
  font-weight: 600;
  font-size: 14px;
  color: %(textStrong)s;
  margin-top: 12px;
  margin-bottom: 4px;
}

/* ----- Caption Labels ----- */
QLabel[caption="true"] {
  font-size: 12px;
  color: %(muted)s;
}

QFormLayout > QLabel {
  font-weight: 500;
  color: %(text)s;
  margin-right: 4px;
}


QLabel[caption="true"][status="success"] { color: rgb(0, 128, 0); }
QLabel[caption="true"][status="warning"] { color: rgb(255, 140, 0); }
QLabel[caption="true"][status="error"]   { color: rgb(178, 34, 34); }

/* ----- Calendar ----- */
QCalendarWidget {
  background: %(surface)s;
  border: 1px solid %(border)s;
  border-radius: %(radius)s;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
  background: %(surface)s;
  border-bottom: 1px solid %(border)s;
}
QCalendarWidget QToolButton {
  padding: 4px 8px;
  border-radius: %(radius)s;
}
QCalendarWidget QToolButton:hover {
  background: %(rowHover)s;
}
/* Days view hover/selection */
QCalendarWidget QAbstractItemView::item:hover {
  background: %(rowHover)s;
}
QCalendarWidget QAbstractItemView::item:selected {
  background: %(primary)s;
  color: %(onPrimary)s;
}
/* Today outline */
QCalendarWidget QAbstractItemView::item:enabled:selected:active {
  outline: none;
}
QCalendarWidget QAbstractItemView::item:enabled {
  padding: 2px;
}


"""

def build_qss(tokens: dict) -> str:
    return BASE_QSS % tokens
