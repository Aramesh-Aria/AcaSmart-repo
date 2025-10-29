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
QPushButton[variant="primary"]  { background: %(primary)s; color: %(onPrimary)s; }
QPushButton[variant="secondary"]{ background: %(surface)s; color: %(text)s; border:1px solid %(border)s; }
QPushButton[variant="ghost"]    { background: transparent; color: %(text)s; border: none; }
QPushButton[variant="danger"]   { background: %(error)s; color: white; }

QPushButton[variant="secondary"]:hover { background: %(rowHover)s; }
QPushButton[variant="ghost"]:hover     { background: %(rowHover)s; }

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




"""

def build_qss(tokens: dict) -> str:
    return BASE_QSS % tokens
