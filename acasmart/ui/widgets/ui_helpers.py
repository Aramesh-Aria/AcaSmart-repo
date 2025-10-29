from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QFrame

def make_card(widget: QFrame) -> QFrame:
    widget.setObjectName("Card")
    return widget

def make_badge(label: QLabel, status: str = "info") -> QLabel:
    label.setObjectName("Badge")
    label.setProperty("status", status)
    label.style().unpolish(label); label.style().polish(label)
    return label

def as_button(btn: QPushButton, variant: str = "primary") -> QPushButton:
    btn.setProperty("variant", variant)
    btn.style().unpolish(btn); btn.style().polish(btn)
    return btn
