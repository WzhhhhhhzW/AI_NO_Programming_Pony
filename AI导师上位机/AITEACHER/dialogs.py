import os

from styles import (dialog_stylesheet, dialog_panel_style,
                    dialog_readonly_text_style, dialog_accent_title_color)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
                             QPushButton, QLineEdit, QFormLayout, QDialogButtonBox,
                             QComboBox, QFileDialog, QCheckBox, QMessageBox,
                             QSizePolicy, QSlider, QWidget)

from flasher import list_serial_ports
from project_manager import list_templates



def _theme(parent) -> str:
    """从主窗口取当前主题；拿不到就用暗色。"""
    return getattr(parent, "current_theme", "dark")


class PathLabel(QLabel):
    """单行显示一个路径，放不下就中间省略，完整值在 tooltip 里。

    不能用 setWordWrap：QFormLayout 不做 height-for-width，换行后的第二行
    算不进行高，会被下一行盖掉（"当前工程"那一行就是这么糊掉的）。
    """

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._full = text
        self.setToolTip(text)
        # Ignored 宽度策略：不让这个长字符串把整个对话框撑宽
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setText(self.fontMetrics().elidedText(
            self._full, Qt.TextElideMode.ElideMiddle, self.width()))

class ConceptDialog(QDialog):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"核心原理解析: {title}")
        self.resize(650, 520)
        
        # 主题跟随主窗口（parent），亮色模式下不再固定暗色
        self.setStyleSheet(dialog_stylesheet(_theme(parent), accent_all=True))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        lbl_title = QLabel(f"📖 {title}")
        lbl_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {dialog_accent_title_color(_theme(parent))}; margin-bottom: 4px;")
        layout.addWidget(lbl_title)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setMarkdown(content)
        text_edit.setStyleSheet(dialog_readonly_text_style(_theme(parent)))
        layout.addWidget(text_edit)

        btn_close = QPushButton("我懂了")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class APISettingsDialog(QDialog):
    def __init__(self, api_key="", api_base_url="", endpoint_id="", power=1,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 参数设置")
        self.resize(520, 340)

        # 主题跟随主窗口（parent），亮色模式下不再固定暗色
        self.setStyleSheet(dialog_stylesheet(_theme(parent), "btn_save"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.edit_url = QLineEdit(api_base_url)
        self.edit_url.setPlaceholderText("留空则使用系统默认")
        form.addRow("base_url:", self.edit_url)

        self.edit_key = QLineEdit(api_key)
        self.edit_key.setPlaceholderText("留空则使用系统默认")
        form.addRow("api_key:", self.edit_key)

        self.edit_model = QLineEdit(endpoint_id)
        self.edit_model.setPlaceholderText("留空则使用系统默认")
        form.addRow("model:", self.edit_model)

        form.addRow("档位:", self._power_widget(power))

        layout.addLayout(form)

        btn_box = QDialogButtonBox()
        btn_save = btn_box.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_save.setObjectName("btn_save")
        btn_cancel = btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _power_widget(self, power: int):
        """三挡滑块。刻度只写快慢，不写背后是什么——学生不需要知道。"""
        box = QVBoxLayout()
        box.setSpacing(2)

        self.slider_power = QSlider(Qt.Orientation.Horizontal)
        self.slider_power.setRange(0, 2)
        self.slider_power.setSingleStep(1)
        self.slider_power.setPageStep(1)
        self.slider_power.setValue(power if 0 <= power <= 2 else 1)
        self.slider_power.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_power.setTickInterval(1)
        box.addWidget(self.slider_power)

        ticks = QHBoxLayout()
        ticks.setContentsMargins(0, 0, 0, 0)
        for i, (text, align) in enumerate((
                ("快", Qt.AlignmentFlag.AlignLeft),
                ("均衡", Qt.AlignmentFlag.AlignHCenter),
                ("细致", Qt.AlignmentFlag.AlignRight))):
            lbl = QLabel(text)
            lbl.setAlignment(align | Qt.AlignmentFlag.AlignTop)
            lbl.setStyleSheet("font-size: 11px; opacity: 0.7;")
            ticks.addWidget(lbl, 1)
            if i == 2:
                lbl.setToolTip("往右更慢、更贵，但复杂改动更容易一次做对")
        box.addLayout(ticks)

        holder = QWidget()
        holder.setLayout(box)
        return holder

    def get_values(self):
        return (self.edit_key.text().strip(),
                self.edit_url.text().strip(),
                self.edit_model.text().strip(),
                self.slider_power.value())


class FlashDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("一键烧录设置")
        self.resize(640, 300)

        # 主题跟随主窗口（parent），亮色模式下不再固定暗色
        self.setStyleSheet(dialog_stylesheet(_theme(parent), "btn_flash_start"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        rfp_row = QHBoxLayout()
        self.edit_rfp = QLineEdit(cfg.get("rfp_path", ""))
        self.edit_rfp.setPlaceholderText("rfp-cli 可执行文件路径")
        btn_rfp = QPushButton("浏览")
        btn_rfp.clicked.connect(self._pick_rfp)
        rfp_row.addWidget(self.edit_rfp)
        rfp_row.addWidget(btn_rfp)
        form.addRow("rfp-cli:", rfp_row)

        port_row = QHBoxLayout()
        self.combo_port = QComboBox()
        self.combo_port.setEditable(True)
        self._refresh_ports(cfg.get("port", ""))
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(lambda: self._refresh_ports(self.combo_port.currentText()))
        port_row.addWidget(self.combo_port, 1)
        port_row.addWidget(btn_refresh)
        form.addRow("串口:", port_row)

        hex_row = QHBoxLayout()
        self.edit_hex = QLineEdit(cfg.get("hex_path", ""))
        self.edit_hex.setPlaceholderText("工程 Debug 目录下的 .hex / .srec 文件")
        btn_hex = QPushButton("浏览")
        btn_hex.clicked.connect(self._pick_hex)
        hex_row.addWidget(self.edit_hex)
        hex_row.addWidget(btn_hex)
        form.addRow("固件文件:", hex_row)

        self.edit_template = QLineEdit(cfg.get("template", ""))
        self.edit_template.setToolTip("烧录命令模板，{rfp} {port} {hex} 为占位符，参数含义见 RFP 命令行手册")
        form.addRow("命令模板:", self.edit_template)

        layout.addLayout(form)

        hint = QLabel("提示：烧录前请将开发板 BOOT 开关拨到 ON 并重新上电。")
        hint.setStyleSheet("color: #8E8E93; font-size: 12px;")
        layout.addWidget(hint)

        btn_box = QDialogButtonBox()
        btn_start = btn_box.addButton("🔥 开始烧录", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_start.setObjectName("btn_flash_start")
        btn_cancel = btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _refresh_ports(self, current):
        self.combo_port.clear()
        self.combo_port.addItems(list_serial_ports())
        if current:
            self.combo_port.setCurrentText(current)

    def _pick_rfp(self):
        fname, _ = QFileDialog.getOpenFileName(self, "选择 rfp-cli", "", "可执行文件 (rfp-cli* *.exe);;All Files (*.*)")
        if fname:
            self.edit_rfp.setText(fname)

    def _pick_hex(self):
        fname, _ = QFileDialog.getOpenFileName(self, "选择固件文件", "", "固件 (*.hex *.srec *.mot *.bin);;All Files (*.*)")
        if fname:
            self.edit_hex.setText(fname)

    def get_values(self):
        return {
            "rfp_path": self.edit_rfp.text().strip(),
            "port": self.combo_port.currentText().strip(),
            "hex_path": self.edit_hex.text().strip(),
            "template": self.edit_template.text().strip(),
        }


class BuildDialog(QDialog):
    def __init__(self, cfg, project_root="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("一键编译设置")
        self.resize(640, 240)

        # 主题跟随主窗口（parent），亮色模式下不再固定暗色
        self.setStyleSheet(dialog_stylesheet(_theme(parent), "btn_build_start"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        # 工程路径不在这里选：它由主界面的【打开工程】唯一决定，
        # 这里只显示，避免出现两个互相打架的"当前工程"
        lbl_project = PathLabel(project_root or "（未打开工程）")
        form.addRow("当前工程:", lbl_project)

        tc_row = QHBoxLayout()
        self.edit_toolchain = QLineEdit(cfg.get("toolchain_bin", ""))
        self.edit_toolchain.setPlaceholderText("含 arm-none-eabi-gcc 的 bin 目录")
        btn_tc = QPushButton("浏览")
        btn_tc.clicked.connect(self._pick_toolchain)
        tc_row.addWidget(self.edit_toolchain)
        tc_row.addWidget(btn_tc)
        form.addRow("工具链:", tc_row)

        mk_row = QHBoxLayout()
        self.edit_make = QLineEdit(cfg.get("make_path", ""))
        self.edit_make.setPlaceholderText("make 可执行文件（需 GNU Make 4.0+）")
        btn_mk = QPushButton("浏览")
        btn_mk.clicked.connect(self._pick_make)
        mk_row.addWidget(self.edit_make)
        mk_row.addWidget(btn_mk)
        form.addRow("make:", mk_row)

        layout.addLayout(form)

        self.chk_full = QCheckBox("彻底重编（先 make clean，慢约 10 倍，仅在结果异常时勾选）")
        self.chk_full.setChecked(False)
        layout.addWidget(self.chk_full)

        hint = QLabel("提示：编译前会自动删除旧固件，产出的 .srec 会自动填入烧录窗口的固件栏。")
        hint.setStyleSheet("color: #8E8E93; font-size: 12px;")
        layout.addWidget(hint)

        btn_box = QDialogButtonBox()
        btn_start = btn_box.addButton("🔨 开始编译", QDialogButtonBox.ButtonRole.AcceptRole)
        btn_start.setObjectName("btn_build_start")
        btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _pick_toolchain(self):
        d = QFileDialog.getExistingDirectory(self, "选择工具链 bin 目录", self.edit_toolchain.text())
        if d:
            self.edit_toolchain.setText(d)

    def _pick_make(self):
        fname, _ = QFileDialog.getOpenFileName(self, "选择 make", "", "可执行文件 (make* *.exe);;All Files (*.*)")
        if fname:
            self.edit_make.setText(fname)

    def get_values(self):
        return {
            "toolchain_bin": self.edit_toolchain.text().strip(),
            "make_path": self.edit_make.text().strip(),
            "full_rebuild": self.chk_full.isChecked(),
        }


class ProjectCreateDialog(QDialog):
    """Dialog for creating a new Renesas RA project from a template."""

    def __init__(self, workspace_dir="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建瑞萨 RA 工程")
        self.resize(560, 400)

        # 主题跟随主窗口（parent），亮色模式下不再固定暗色
        self.setStyleSheet(dialog_stylesheet(_theme(parent), "btn_create"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title
        title = QLabel("📁 从模板创建新工程")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {dialog_accent_title_color(_theme(parent))}; margin-bottom: 4px;")
        layout.addWidget(title)

        # Template selection
        form = QFormLayout()
        form.setSpacing(10)

        self.combo_template = QComboBox()
        self._templates = list_templates()
        for t in self._templates:
            self.combo_template.addItem(t["display_name"], t["name"])
        self.combo_template.currentIndexChanged.connect(self._on_template_changed)
        form.addRow("工程模板:", self.combo_template)

        # Template description
        self.lbl_desc = QLabel("")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet(dialog_panel_style(_theme(parent)))
        layout.addWidget(self.lbl_desc)

        # Project name
        self.edit_name = QLineEdit("")
        self.edit_name.setPlaceholderText("例如: MyRobohorse")
        form.addRow("工程名称:", self.edit_name)

        # Workspace directory
        ws_row = QHBoxLayout()
        self.edit_workspace = QLineEdit(workspace_dir)
        self.edit_workspace.setPlaceholderText("纯英文路径，如 D:\\e2s_workspace")
        btn_ws = QPushButton("浏览")
        btn_ws.clicked.connect(self._pick_workspace)
        ws_row.addWidget(self.edit_workspace)
        ws_row.addWidget(btn_ws)
        form.addRow("工作空间:", ws_row)

        layout.addLayout(form)

        # Open in RASC checkbox
        self.chk_rasc = QCheckBox("创建后在 RASC 中查看 FSP 配置")
        self.chk_rasc.setChecked(False)
        layout.addWidget(self.chk_rasc)

        # Warning label
        self.lbl_warn = QLabel("💡 提示：工作空间路径和工程名称不要包含中文或空格（编译工具链限制）。")
        self.lbl_warn.setStyleSheet("color: #cca700; font-size: 11px;")
        self.lbl_warn.setWordWrap(True)
        layout.addWidget(self.lbl_warn)

        layout.addStretch()

        # Buttons
        btn_box = QDialogButtonBox()
        self.btn_create = btn_box.addButton("创建工程", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_create.setObjectName("btn_create")
        btn_box.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        # Init
        self._on_template_changed(0)

    def _on_template_changed(self, index):
        if 0 <= index < len(self._templates):
            t = self._templates[index]
            self.lbl_desc.setText(t["description"])
            # Auto-suggest project name from template
            if not self.edit_name.text():
                self.edit_name.setText(t["name"])

    def _pick_workspace(self):
        d = QFileDialog.getExistingDirectory(self, "选择工作空间目录", self.edit_workspace.text())
        if d:
            self.edit_workspace.setText(d)

    def _validate_and_accept(self):
        workspace = self.edit_workspace.text().strip()
        name = self.edit_name.text().strip()

        # Validate workspace
        if not workspace:
            QMessageBox.warning(self, "输入不完整", "请选择工作空间目录。")
            return
        if any(ord(ch) > 127 for ch in workspace):
            QMessageBox.warning(
                self, "路径含中文",
                "工作空间路径里有中文或特殊字符，编译工具链无法正确处理。\n"
                "请选择纯英文路径（如 D:\\e2s_workspace）。"
            )
            return
        if not os.path.isdir(workspace):
            QMessageBox.warning(self, "目录不存在", f"工作空间目录不存在:\n{workspace}")
            return

        # Validate project name
        if not name:
            QMessageBox.warning(self, "输入不完整", "请输入工程名称。")
            return
        if any(ch in r'\/:*?"<>|' for ch in name):
            QMessageBox.warning(self, "非法字符", "工程名称包含非法字符。")
            return
        target = os.path.join(workspace, name)
        if os.path.exists(target):
            QMessageBox.warning(self, "工程已存在", f"目标路径已存在:\n{target}\n请更换工程名称。")
            return

        self.accept()

    def get_values(self) -> dict:
        """Return the user's selections."""
        idx = self.combo_template.currentIndex()
        template_name = self._templates[idx]["name"] if 0 <= idx < len(self._templates) else ""
        return {
            "template_name": template_name,
            "project_name": self.edit_name.text().strip(),
            "workspace_dir": self.edit_workspace.text().strip(),
            "open_in_rasc": self.chk_rasc.isChecked(),
        }
