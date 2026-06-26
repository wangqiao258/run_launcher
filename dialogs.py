from PyQt5.QtWidgets import (QDialog, QFormLayout, QVBoxLayout, QLabel,
                             QLineEdit, QSpinBox, QPushButton, QCheckBox)
from PyQt5.QtCore import Qt
import config

STYLE_DLG = "QDialog { background: #333; } QLabel { color: white; } QLineEdit { background: #555; color: white; border: 1px solid #777; padding: 4px; } QPushButton { background: #555; color: white; border: 1px solid #777; padding: 6px 20px; } QPushButton:hover { background: #666; }"
STYLE_INPUT = "background: #555; color: white; border: 1px solid #777; padding: 4px;"
STYLE_BTN = "background: #555; color: white; border: 1px solid #777; padding: 6px;"

class SettingsDialog(QDialog):
    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.config_data = config_data
        self.setWindowTitle("设置")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.resize(320, 220)

        form = QFormLayout(self)
        self.de_title = QLineEdit(config_data.get("title", "Run Launcher"))
        self.de_title.setStyleSheet(STYLE_INPUT)
        self.sb_w = QSpinBox()
        self.sb_w.setRange(200, 2000); self.sb_w.setValue(config_data.get("window_width", 420))
        self.sb_w.setStyleSheet(STYLE_INPUT)
        self.sb_h = QSpinBox()
        self.sb_h.setRange(200, 2000); self.sb_h.setValue(config_data.get("window_height", 480))
        self.sb_h.setStyleSheet(STYLE_INPUT)
        self.cb_autostart = QCheckBox("开机自启动")
        self.cb_autostart.setChecked(config.is_auto_start_enabled())
        self.cb_autostart.setStyleSheet("color: white;")

        form.addRow("标题:", self.de_title)
        form.addRow("宽度:", self.sb_w)
        form.addRow("高度:", self.sb_h)
        form.addRow("", self.cb_autostart)

        btn = QPushButton("确定")
        btn.setStyleSheet(STYLE_BTN)
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def get_values(self):
        return {
            "title": self.de_title.text(),
            "width": self.sb_w.value(),
            "height": self.sb_h.value(),
            "autostart": self.cb_autostart.isChecked(),
        }

class InputDialog(QDialog):
    def __init__(self, parent, title, label, default=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE_DLG)
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self.ed = QLineEdit(default)
        self.ed.setStyleSheet(STYLE_INPUT)
        layout.addWidget(self.ed)
        btn = QPushButton("确定")
        btn.setStyleSheet(STYLE_BTN)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_text(self):
        return self.ed.text().strip() if self.result() == QDialog.Accepted else None

class EditItemDialog(QDialog):
    def __init__(self, parent, name, path):
        super().__init__(parent)
        self.setWindowTitle("编辑")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE_DLG)
        self.setFixedWidth(350)
        form = QFormLayout(self)
        self.ed_name = QLineEdit(name)
        self.ed_name.setStyleSheet(STYLE_INPUT)
        self.ed_path = QLineEdit(path)
        self.ed_path.setStyleSheet(STYLE_INPUT)
        form.addRow("名称:", self.ed_name)
        form.addRow("路径:", self.ed_path)
        btn = QPushButton("确定")
        btn.setStyleSheet(STYLE_BTN)
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def get_values(self):
        import os
        name = self.ed_name.text().strip()
        path = self.ed_path.text().strip()
        if name and path and os.path.exists(path):
            return {"name": name, "path": path}
        return None
