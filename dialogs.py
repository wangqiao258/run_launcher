from PyQt5.QtWidgets import (QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QSpinBox, QPushButton, QCheckBox, QFileDialog, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
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
    def __init__(self, parent, name, path, icon_path=""):
        super().__init__(parent)
        self.setWindowTitle("编辑")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE_DLG)
        self.setFixedWidth(420)
        form = QFormLayout(self)
        self.ed_name = QLineEdit(name)
        self.ed_name.setStyleSheet(STYLE_INPUT)
        self.ed_path = QLineEdit(path)
        self.ed_path.setStyleSheet(STYLE_INPUT)
        self.ed_icon = QLineEdit(icon_path or "")
        self.ed_icon.setStyleSheet(STYLE_INPUT)
        self.ed_icon.setPlaceholderText("留空则自动提取；支持 .ico .png .exe .dll")
        icon_row = QWidget()
        icon_row_layout = QHBoxLayout(icon_row)
        icon_row_layout.setContentsMargins(0, 0, 0, 0)
        icon_row_layout.addWidget(self.ed_icon, 1)
        btn_browse = QPushButton("浏览...")
        btn_browse.setStyleSheet(STYLE_BTN)
        btn_browse.clicked.connect(self._pick_icon)
        btn_clear = QPushButton("清空")
        btn_clear.setStyleSheet(STYLE_BTN)
        btn_clear.clicked.connect(lambda: self.ed_icon.setText(""))
        icon_row_layout.addWidget(btn_browse)
        icon_row_layout.addWidget(btn_clear)
        form.addRow("名称:", self.ed_name)
        form.addRow("路径:", self.ed_path)
        form.addRow("图标:", icon_row)
        btn = QPushButton("确定")
        btn.setStyleSheet(STYLE_BTN)
        btn.clicked.connect(self.accept)
        form.addRow(btn)

    def _pick_icon(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择图标",
            self.ed_icon.text() or "",
            "图标文件 (*.ico *.png *.jpg *.jpeg *.bmp *.exe *.dll);;所有文件 (*.*)")
        if f:
            self.ed_icon.setText(f)

    def get_values(self):
        import os
        name = self.ed_name.text().strip()
        path = self.ed_path.text().strip()
        icon_path = self.ed_icon.text().strip()
        if name and path and os.path.exists(path):
            result = {"name": name, "path": path}
            if icon_path and os.path.exists(icon_path):
                result["icon_path"] = icon_path
            return result
        return None


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(STYLE_DLG)
        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Run Launcher")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = QLabel(f"版本 v{config.VERSION}")
        ver.setStyleSheet("color: #ccc;")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        desc = QLabel("Windows 快速启动器\nAlt+Space 全局呼出")
        desc.setStyleSheet("color: #aaa;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)

        row = QHBoxLayout()
        btn_github = QPushButton("GitHub")
        btn_github.setStyleSheet(STYLE_BTN)
        btn_github.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"https://github.com/{config.GITHUB_REPO}")))
        btn_update = QPushButton("检查更新")
        btn_update.setStyleSheet(STYLE_BTN)
        btn_update.clicked.connect(lambda: (self.accept(), parent.check_update(silent=False)))
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(STYLE_BTN)
        btn_close.clicked.connect(self.accept)
        row.addWidget(btn_github)
        row.addWidget(btn_update)
        row.addWidget(btn_close)
        layout.addLayout(row)
