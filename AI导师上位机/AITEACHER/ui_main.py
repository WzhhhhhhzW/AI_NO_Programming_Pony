import os
import time
import datetime
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QFileDialog, QLabel,
                             QLineEdit, QSplitter, QMessageBox, QStatusBar,
                             QComboBox, QFrame, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from loguru import logger
from openai import OpenAI

from config import API_KEY, API_BASE_URL, ENDPOINT_ID
from config import get_api_key, get_api_base_url, get_endpoint_id, load_user_config, save_user_config
from config import get_anthropic_base_url, get_agent_model, get_edit_model
from config import get_power, set_power
from config import load_workspace_config, save_workspace_config
from styles import MODERN_STYLESHEET, LIGHT_STYLESHEET
from dialogs import ConceptDialog, APISettingsDialog, FlashDialog, BuildDialog, ProjectCreateDialog
from ai_worker import AIWorker
from flasher import FlashWorker, load_flash_config, save_flash_config, build_flash_command
from builder import BuildWorker, load_build_config, save_build_config, find_debug_dir
from prompts import ADVISOR_ROLE_PROMPT, BEGINNER_AGENT_PROMPT
import lesson_flow
import project_api
import project_context
import snapshot as snapshot_mod
from lesson_flow import LessonFlow
from chat_view import ChatView
from code_editor import EditorTabs
from project_view import ProjectTree
from output_panel import OutputPanel
from advisor import Advisor, AdvisorConfig, EDIT_TOOLS, READONLY_TOOLS
from build_tool import make_server as make_compile_server
from project_manager import ProjectCreateWorker, open_project_in_rasc

# 初级模式开场那张卡片上的快捷指令。现场不用打字，也保证问题落在
# 模型能一次改对的范围内。
QUICK_COMMANDS = [
    {"icon": "⚡", "label": "走路速度快一倍", "text": "让小马走路的速度快一倍"},
    {"icon": "↩️", "label": "转弯幅度调大", "text": "把小马转弯的幅度调大一些"},
    {"icon": "🚀", "label": "开机就前进", "text": "让小马一上电就自己开始前进，不用手机发指令"},
    {"icon": "🐕", "label": "多摇几下尾巴", "text": "摇尾巴的时候多摇几下"},
    {"icon": "😀", "label": "屏幕显示表情", "text": "前进的时候在 OLED 屏幕上显示对应的表情"},
]


class CoderUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Renesas 机器马 AI 导师 V15.0")
        self.resize(1380, 840)
        self.current_code = ""
        # 当前工程根目录。打开工程目录后由它统一回答"学生在做哪个工程"，
        # 编译、RASC、AI 都读这一个，不再各自去猜。
        self.project_root = ""
        self.last_ai_response = ""
        self.history = []
        self.current_difficulty = "初级"
        self.current_theme = "dark"

        # 高级模式课程进度由程序持有（不再让模型从对话里猜 Step）
        # 刻意不持久化：每次启动都从第 1 课开始
        self.lessons = LessonFlow()

        # 常驻 agent 会话；_bubble 是当前正在接收流式内容的气泡
        self.advisor = None
        self._advisor_mode = ""      # 会话是按哪个模式开的（换模式要重开）
        self._bubble = None
        self._lesson_synced = -1     # 已经同步给 agent 的课程下标

        # 初级模式：AI 动手前先给 src/ 拍快照，改坏了能一键回退
        self.snapshot = None
        self._act_seq = 0            # 动作条的编号，撤销时按它定位

        # 一轮进行中的计时，见 _lock_send
        self._turn_started = 0.0
        self._turn_hint = ""
        self._turn_timer = QTimer(self)
        self._turn_timer.timeout.connect(self._tick_turn)

        load_user_config()
        self.user_api_key = API_KEY
        self.user_api_base_url = API_BASE_URL
        self.user_endpoint_id = ENDPOINT_ID

        self.setStyleSheet(MODERN_STYLESHEET)

        self.client = None
        self._init_client()
        self.init_ui()
        self._apply_client_state()

    def _init_client(self):
        """只负责建 client；失败时置 None 并禁用发送，不再重建整个界面。"""
        key = self.user_api_key or get_api_key()
        url = self.user_api_base_url or get_api_base_url()
        try:
            self.client = OpenAI(base_url=url, api_key=key)
            self.client_error = ""
        except Exception as e:
            self.client = None
            self.client_error = str(e)
            QMessageBox.critical(self, "AI 初始化失败", f"{e}\n\n对话功能已禁用，其余功能（编译/烧录/新建工程）不受影响。")
        self._apply_client_state()

    def _apply_client_state(self):
        """根据 client 是否可用，开关发送相关控件。"""
        if not hasattr(self, "btn_send"):
            return          # init_ui 还没跑
        ok = self.client is not None
        self.btn_send.setEnabled(ok)
        self.txt_input.setEnabled(ok)
        if ok:
            self.txt_input.setPlaceholderText("在此提问，或点右上角【下一步】推进课程...")
        else:
            self.txt_input.setPlaceholderText("AI 初始化失败，请在 ⚙️ API 设置 中检查配置")
            self.status_bar.showMessage(f"AI 不可用: {self.client_error}")

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # 1. 顶部工具条
        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(38)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(8, 0, 8, 0)
        top_bar_layout.setSpacing(8)

        # 动作按钮
        self.btn_open_project = QPushButton("📂 打开工程")
        self.btn_open_project.clicked.connect(self.open_project_folder)
        self.btn_open_project.setToolTip("打开 e2 studio 工程目录，左侧会列出工程文件")

        self.btn_save = QPushButton("💾 保存代码")
        self.btn_save.clicked.connect(self.save_file)
        self.btn_save.setEnabled(False)

        self.btn_api_settings = QPushButton("⚙️ API 设置")
        self.btn_api_settings.clicked.connect(self.open_api_settings)

        self.btn_build = QPushButton("🔨 一键编译")
        self.btn_build.clicked.connect(self.open_build_dialog)
        self.btn_build.setToolTip("调用 make + arm-none-eabi 工具链编译 e2 studio 工程，产出固件")

        self.btn_flash = QPushButton("🔥 一键烧录")
        self.btn_flash.clicked.connect(self.open_flash_dialog)
        self.btn_flash.setToolTip("通过 rfp-cli 将编译好的 hex 固件烧录到开发板")

        # 项目工程管理按钮
        self.btn_new_project = QPushButton("🆕 新建工程")
        self.btn_new_project.clicked.connect(self.open_create_project_dialog)
        self.btn_new_project.setToolTip("从模板创建瑞萨 RA 工程，自动生成项目骨架和 FSP 配置")

        self.btn_rasc = QPushButton("⚙️ RASC配置")
        self.btn_rasc.clicked.connect(self.open_in_rasc_current)
        self.btn_rasc.setToolTip("在 RA Smart Configurator 中打开当前工程的 FSP 配置")
        self.btn_rasc.setEnabled(False)

        # 主题一键快速切换按钮
        self.btn_theme_toggle = QPushButton("☀️ 亮色模式")
        self.btn_theme_toggle.clicked.connect(self.toggle_theme)

        # 右侧分级控制
        self.lbl_diff = QLabel("阶段")
        self.lbl_diff.setObjectName("lbl_diff")
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["初级（直接生成）", "高级（引导思考）"])
        self.difficulty_combo.currentIndexChanged.connect(self.on_difficulty_changed)

        # 按功能分组，组间加竖线分隔，比一长排按钮好扫
        for group in (
            (self.btn_open_project, self.btn_save),
            (self.btn_new_project, self.btn_rasc),
            (self.btn_build, self.btn_flash),
        ):
            for btn in group:
                top_bar_layout.addWidget(btn)
            top_bar_layout.addWidget(self._make_separator())

        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.lbl_diff)
        top_bar_layout.addWidget(self.difficulty_combo)
        top_bar_layout.addWidget(self._make_separator())
        top_bar_layout.addWidget(self.btn_api_settings)
        top_bar_layout.addWidget(self.btn_theme_toggle)

        main_layout.addWidget(top_bar)

        # 2. 左右大分栏区域
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(4)

        # 左侧：工作区
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        self.project_tree = ProjectTree()
        self.project_tree.setObjectName("project_tree_panel")
        self.project_tree.file_activated.connect(self.open_file_path)
        self.project_tree.file_created.connect(self.open_file_path)

        self.editor = EditorTabs(theme=self.current_theme)
        self.editor.setObjectName("editor_tabs_panel")
        self.editor.dirty_changed.connect(lambda _d: self.check_save_button())
        self.editor.current_file_changed.connect(self._on_editor_file_changed)
        
        # 编辑器下面挂输出面板。默认收起，编译时自动展开——把几十行
        # arm-none-eabi-objcopy 塞进对话区实在没法看，也点不动
        self.output = OutputPanel(theme=self.current_theme)
        self.output.problem_activated.connect(self._goto_problem)
        self.output.closed.connect(lambda: self.show_output(False))

        editor_side = QSplitter(Qt.Orientation.Vertical)
        editor_side.setHandleWidth(4)
        editor_side.addWidget(self.editor)
        editor_side.addWidget(self.output)
        editor_side.setStretchFactor(0, 1)
        editor_side.setStretchFactor(1, 0)
        editor_side.setCollapsible(0, False)
        self.editor_split = editor_side
        self.output.hide()

        left_split = QSplitter(Qt.Orientation.Horizontal)
        left_split.setHandleWidth(4)
        left_split.addWidget(self.project_tree)
        left_split.addWidget(editor_side)
        left_split.setStretchFactor(0, 22)
        left_split.setStretchFactor(1, 78)
        left_split.setSizes([210, 700])
        left_layout.addWidget(left_split, 1)

        # 右侧：聊天区
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        
        # 聊天区自己的头部：左边标题，右边课程导航（导航属于对话，不属于文件操作）
        chat_header = QHBoxLayout()
        chat_header.setSpacing(6)
        lbl_chat = QLabel("💬 AI 导师")
        lbl_chat.setStyleSheet("font-weight: bold; color: #5865f2;")

        self.btn_lesson_prev = QPushButton("◀ 上一步")
        self.btn_lesson_prev.setObjectName("btn_lesson_nav")
        self.btn_lesson_prev.setToolTip("回到上一课")
        self.btn_lesson_prev.clicked.connect(self.go_prev_lesson)

        # 课程标题只读显示——课程只能靠上/下一步连续推进，不提供跳转
        self.lbl_lesson = QLabel("")
        self.lbl_lesson.setObjectName("lbl_lesson")
        self.lbl_lesson.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_lesson_next = QPushButton("下一步 ▶")
        self.btn_lesson_next.setObjectName("btn_lesson_nav")
        self.btn_lesson_next.setToolTip("进入下一课")
        self.btn_lesson_next.clicked.connect(self.go_next_lesson)

        chat_header.addWidget(lbl_chat)
        chat_header.addStretch()
        chat_header.addWidget(self.btn_lesson_prev)
        chat_header.addWidget(self.lbl_lesson)
        chat_header.addWidget(self.btn_lesson_next)

        # 细进度条，贴在课程导航下面
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("lesson_progress")
        self.progress_bar.setRange(0, self.lessons.total)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)

        self.chat_log = ChatView(theme=self.current_theme)
        self.chat_log.setObjectName("chat_log")
        self.chat_log.action.connect(self._on_chat_action)
        
        # 输入排版
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.txt_input = QLineEdit()
        self.txt_input.setObjectName("txt_input")
        self.txt_input.setPlaceholderText("在此提问或输入 '教我做机器马' 开始...")
        self.txt_input.returnPressed.connect(self.start_chat)

        self.btn_send = QPushButton("发送")
        self.btn_send.setObjectName("btn_send")
        self.btn_send.clicked.connect(self.start_chat)

        self.btn_explain = QPushButton("📚 知识详解")
        self.btn_explain.setObjectName("btn_explain")
        self.btn_explain.setToolTip("深入讲解当前开发步骤中的单片机原理知识")
        self.btn_explain.clicked.connect(self.explain_concept)
        self.btn_explain.setEnabled(False)

        input_layout.addWidget(self.txt_input)
        input_layout.addWidget(self.btn_send)
        input_layout.addWidget(self.btn_explain)

        right_layout.addLayout(chat_header)
        right_layout.addWidget(self.progress_bar)
        right_layout.addWidget(self.chat_log, 1)   # 1 = 占满剩余竖直空间
        right_layout.addLayout(input_layout)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)
        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统就绪。")

        # 默认是初级模式，课程导航先隐藏
        self._update_lesson_nav()
        self._apply_project_state()
        # 卡片要摆在最前面，所以先放卡片再恢复工程
        # （ChatView 会把页面加载完成前的调用先攒着，这里直接调就行）
        self._show_intro_card()
        self._restore_last_project()
        self._beginner_project_hint()

    def toggle_theme(self):
        if self.current_theme == "dark":
            self.setStyleSheet(LIGHT_STYLESHEET)
            self.current_theme = "light"
            self.btn_theme_toggle.setText("🌙 暗色模式")
            # 亮色模式下的进度条样式
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #d2d2d7;
                    border-radius: 4px;
                    text-align: center;
                    color: #1d1d1f;
                    background-color: #ffffff;
                }
                QProgressBar::chunk {
                    background-color: #0078d4;
                    border-radius: 3px;
                }
            """)
        else:
            self.setStyleSheet(MODERN_STYLESHEET)
            self.current_theme = "dark"
            self.btn_theme_toggle.setText("☀️ 亮色模式")
            # 暗色模式下的进度条样式
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #3e3e42;
                    border-radius: 4px;
                    text-align: center;
                    color: #ffffff;
                    background-color: #252526;
                }
                QProgressBar::chunk {
                    background-color: #007acc;
                    border-radius: 3px;
                }
            """)
            
        self.refresh_chat_display()
        self.editor.set_theme(self.current_theme)
        self.output.apply_theme(self.current_theme)

    def open_api_settings(self):
        dialog = APISettingsDialog(
            api_key=self.user_api_key,
            api_base_url=self.user_api_base_url,
            endpoint_id=self.user_endpoint_id,
            power=get_power(),
            parent=self
        )
        if dialog.exec():
            key, url, model, power = dialog.get_values()
            self.user_api_key = key
            self.user_api_base_url = url
            self.user_endpoint_id = model
            changed = power != get_power()
            set_power(power)
            save_user_config(key, url, model, power)
            self._init_client()
            # 档位换了要重开会话才生效——会话建的时候就把模型定死了
            if changed:
                self._close_advisor()
            self.add_log("System", "API 参数已保存")

    def open_build_dialog(self):
        if not self.project_root:
            QMessageBox.warning(self, "未打开工程", "请先点【📂 打开工程】选择工程目录。")
            return

        cfg = load_build_config()
        dialog = BuildDialog(cfg, project_root=self.project_root, parent=self)
        if not dialog.exec():
            return

        cfg = dialog.get_values()
        full_rebuild = cfg.pop("full_rebuild", False)   # 每次都要显式勾，不进配置文件
        save_build_config(cfg)
        self._start_build(full_rebuild=full_rebuild)

    def _start_build(self, full_rebuild: bool = False):
        """真正发起编译。设置对话框和对话区里的按钮都走这里。"""
        if not self.project_root:
            QMessageBox.warning(self, "未打开工程", "请先点【📂 打开工程】选择工程目录。")
            return
        # make 编的是磁盘上的文件，不保存就等于编了个旧版本还以为是新的
        if not self._confirm_dirty("有未保存的改动",
                                   "不保存的话，编进固件的还是磁盘上的旧代码。"):
            return
        cfg = load_build_config()

        debug_dir = find_debug_dir(self.project_root)
        if not debug_dir:
            QMessageBox.warning(self, "找不到构建目录",
                                "该工程目录下没有含 makefile 的 Debug/ 目录。\n"
                                "请先在 e2 studio 里生成并构建过一次该工程。")
            return
        # 实测：工程路径含中文/非 ASCII 时，gcc 与 ld 对路径编码的期望不一致，
        # 无论哪种编码链接或编译必有一头失败，因此直接拦截
        if any(ord(ch) > 127 for ch in self.project_root):
            QMessageBox.warning(self, "工程路径含中文",
                                "工程路径里有中文或特殊字符，编译工具链无法正确处理。\n"
                                "请把 e2 studio 工作空间放在纯英文路径下（如 D:\\e2s_workspace）。")
            return

        self.btn_build.setEnabled(False)
        self.status_bar.showMessage("编译中...")
        # 详细日志进下面的面板，对话区只留结论
        self.show_output(True)
        self.output.start_run(f"🔨 开始编译：{os.path.basename(self.project_root)}")
        self.add_log("System", "🔨 正在编译…（详细输出见编辑器下方的面板）")

        logger.info("开始编译 debug_dir={} full_rebuild={}", debug_dir, full_rebuild)
        self.build_worker = BuildWorker(debug_dir, cfg["make_path"], cfg["toolchain_bin"],
                                        full_rebuild=full_rebuild)
        self.build_worker.output_line.connect(self.output.append)
        self.build_worker.build_finished.connect(self.on_build_finished)
        self.build_worker.start()

    def on_build_finished(self, success, message, firmware_path):
        logger.info("编译结束 success={} msg={} 固件={}", success, message, firmware_path)
        self.btn_build.setEnabled(True)
        self.status_bar.clearMessage()

        # 问题列表 + 编辑器行号旁的红底，都按同一份解析结果来
        diagnostics = self.build_worker.diagnostics(self.project_root)
        self.output.append_result(message, success)
        self.output.set_problems(diagnostics)
        self.output.set_summary(message, success)
        by_path = {}
        for d in diagnostics:
            if d["kind"] != "warning":
                by_path.setdefault(d["abs_path"], []).append(d["line"])
        self.editor.set_errors(by_path)

        errors = sum(1 for d in diagnostics if d["kind"] != "warning")
        if not success:
            tail = f"，{errors} 处错误（双击下方【问题】里的条目跳到出错的行）" if errors else ""
            self.add_log("System", f"❌ <b>{message}</b>{tail}")
            return

        # 编译成功 ⇒ 磁盘上的改动都进固件了，绿色标记不用再挂着
        self.editor.clear_marks()
        if firmware_path:
            # 编译产物自动填入烧录配置的固件栏
            flash_cfg = load_flash_config()
            flash_cfg["hex_path"] = firmware_path
            save_flash_config(flash_cfg)
            self.add_log("System", f"✅ <b>{message}</b>！固件已生成：{os.path.basename(firmware_path)}"
                                    f"<br>已自动填入烧录窗口，点击 🔥 一键烧录即可。")
        else:
            self.add_log("System", f"✅ <b>{message}</b>，但未在构建目录找到 .srec/.hex 产物。")

    def open_flash_dialog(self):
        cfg = load_flash_config()
        dialog = FlashDialog(cfg, parent=self)
        if not dialog.exec():
            return

        cfg = dialog.get_values()
        save_flash_config(cfg)

        missing = []
        if not cfg["rfp_path"]:
            missing.append("rfp-cli 路径")
        if not cfg["port"]:
            missing.append("串口")
        if not cfg["hex_path"]:
            missing.append("固件文件")
        if missing:
            QMessageBox.warning(self, "烧录设置不完整", "请先填写：" + "、".join(missing))
            return
        if not os.path.exists(cfg["hex_path"]):
            QMessageBox.warning(self, "文件不存在", f"找不到固件文件：\n{cfg['hex_path']}")
            return

        command = build_flash_command(cfg["template"], cfg["rfp_path"], cfg["port"], cfg["hex_path"])
        self.btn_flash.setEnabled(False)
        self.status_bar.showMessage("烧录中...")
        # 显示固件的修改时间和大小，避免误烧旧固件而不自知
        st = os.stat(cfg["hex_path"])
        mtime = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%m-%d %H:%M")
        self.add_log("System", f"🔥 开始烧录 {os.path.basename(cfg['hex_path'])}"
                               f"（修改于 {mtime}，{st.st_size} 字节）→ {cfg['port']}")
        if datetime.datetime.now().timestamp() - st.st_mtime > 3600:
            self.add_log("System", "⚠️ 注意：该固件文件是 1 小时前生成的。如果你刚重新编译过，"
                                    "请确认选择的是最新产出的 .srec/.hex（在工程的 Debug 目录下）。")

        self.flash_worker = FlashWorker(command)
        self.flash_worker.output_line.connect(lambda line: self.add_log("System", line))
        self.flash_worker.flash_finished.connect(self.on_flash_finished)
        self.flash_worker.start()

    def on_flash_finished(self, success, message):
        self.btn_flash.setEnabled(True)
        self.status_bar.clearMessage()
        if success:
            self.add_log("System", f"✅ <b>{message}</b>！重新上电（BOOT 拨回 OFF）即可看到运行效果。")
        else:
            self.add_log("System", f"❌ <b>{message}</b>")

    # ---------- 工程管理 ----------

    def open_create_project_dialog(self):
        """Open the 'New Project' dialog and create a project from template."""
        ws_cfg = load_workspace_config()
        ws = ws_cfg.get("workspace_dir", "")
        dialog = ProjectCreateDialog(workspace_dir=ws, parent=self)
        if not dialog.exec():
            return

        values = dialog.get_values()
        save_workspace_config(workspace_dir=values["workspace_dir"])

        self.btn_new_project.setEnabled(False)
        self.status_bar.showMessage("正在创建工程...")
        self.add_log("System", f"📁 正在创建工程 <b>{values['project_name']}</b> ...")

        self.pm_worker = ProjectCreateWorker(
            values["template_name"],
            values["workspace_dir"],
            values["project_name"],
        )
        self.pm_worker.progress_update.connect(
            lambda msg, pct: self.status_bar.showMessage(f"创建工程: {msg}")
        )
        self.pm_worker.creation_finished.connect(
            lambda success, detail, project_dir: self._on_project_created(
                success, detail, project_dir, values["open_in_rasc"]
            )
        )
        self.pm_worker.start()

    def _on_project_created(self, success: bool, detail: str, project_dir: str, open_rasc: bool):
        self.btn_new_project.setEnabled(True)
        self.status_bar.clearMessage()

        if not success:
            self.add_log("System", f"❌ <b>创建失败:</b> {detail}")
            QMessageBox.warning(self, "工程创建失败", detail)
            return

        # 走和"打开工程"完全相同的路径，避免两套状态
        self.set_project_root(project_dir)

        self.add_log("System",
            f"✅ <b>工程创建成功!</b><br>"
            f"📂 路径: {project_dir}<br>"
            f"🔨 编译设置已自动配置，可直接点击一键编译。<br>"
            f"📝 已加载 hal_entry.c 到编辑器。"
        )

        # Optionally open in RASC
        if open_rasc:
            launched, msg = open_project_in_rasc(project_dir)
            if launched:
                self.add_log("System", f"🔧 {msg}<br>请在 RASC 中查看 FSP 配置，确认无误后点击 <b>Generate Project Content</b>。")
            else:
                self.add_log("System", f"⚠️ {msg}")
                QMessageBox.information(self, "RASC 不可用", msg)

    def open_in_rasc_current(self):
        """在 RASC / e2 studio 里打开当前工程的 FSP 配置。"""
        if not project_context.is_project_root(self.project_root):
            QMessageBox.information(self, "不是 RA 工程",
                                    "当前工程里没有 configuration.xml。")
            return
        launched, msg = open_project_in_rasc(self.project_root)
        if launched:
            self.add_log("System", f"🔧 {msg}")
        else:
            self.add_log("System", f"⚠️ {msg}")
            QMessageBox.warning(self, "RASC 不可用", msg)

    def on_difficulty_changed(self, index):
        modes = ["初级", "高级"]
        self.current_difficulty = modes[index]
        self.history.clear()
        self._close_advisor()
        self._update_lesson_nav()
        if self.current_difficulty == "高级":
            if not self.project_root:
                self.add_log("System",
                             "还没打开工程。点左上角【📂 打开工程】选中你的 e2 studio "
                             "工程目录，我才能看到你的代码；第 2 课会讲怎么建。")
            # 进入高级模式直接展示当前这一课，不需要用户说"开始"
            self._render_current_lesson()
        else:
            self._show_beginner_intro()

    # ---------- 初级模式 ----------

    def _show_beginner_intro(self):
        """开场卡片。点一下就发送，现场不用打字。"""
        self._show_intro_card()
        self._beginner_project_hint()

    def _show_intro_card(self):
        if self.current_difficulty != "初级":
            return
        self.chat_log.add_quick(
            "直接说你想让小马做什么",
            "我会读你的工程、改好代码，改完点【编译并准备烧录】就能看效果",
            QUICK_COMMANDS,
        )

    def _beginner_project_hint(self):
        if self.current_difficulty != "初级":
            return
        if not self.project_root:
            self.add_log("System",
                         "还没打开工程。点左上角【📂 打开工程】选中小马工程目录，"
                         "我才能改你的代码。")
        else:
            # 预热会话：首轮冷启动要十几秒，提前建好，学生第一句话就是热的
            self._ensure_advisor()

    def _on_chat_action(self, name: str, params: dict):
        """对话区网页里的按钮点击。见 chat_page.js 的 href()。"""
        logger.info("处理按钮 {} {}", name, params)
        if name == "send":
            text = params.get("text", "")
            if text:
                self.txt_input.setText(text)
                self.start_chat()
        elif name == "open":
            path = params.get("path", "")
            try:
                line = int(params.get("line", "1"))
            except ValueError:
                line = 1
            if path:
                # 带上这个文件的改动行号：AI 一轮改多个文件时，只有排序第一个
                # 会被自动打开并标记，其余要靠学生点这里进去，不传就是白的
                self.editor.goto_line(path, line, self._marks_for(path))
                self.project_tree.reveal(path)
        elif name == "build":
            self._start_build(full_rebuild=False)
        elif name == "undo":
            self._undo_ai_changes(params.get("id", ""))

    # ---------- 输出面板 ----------

    def show_output(self, visible: bool):
        """展开/收起编辑器下面的输出面板。"""
        self.output.setVisible(visible)
        if visible:
            total = self.editor_split.height() or 600
            self.editor_split.setSizes([int(total * 0.62), int(total * 0.38)])

    def _goto_problem(self, path: str, line: int):
        """双击问题列表 → 跳到出错那一行。"""
        logger.info("跳到问题 {}:{}", path, line)
        self.editor.goto_line(path, line)
        self.project_tree.reveal(path)

    def _marks_for(self, path: str) -> list:
        """这个文件在本轮改动里被加/改过的行号；没有就返回空。"""
        if self.snapshot is None or not self.snapshot.has_snapshot:
            return []
        target = os.path.abspath(path)
        for d in self.snapshot.changes():
            if d.abs_path and os.path.abspath(d.abs_path) == target:
                return snapshot_mod.added_lines(d)
        return []

    def _undo_ai_changes(self, act_id: str):
        if self.snapshot is None or not self.snapshot.has_snapshot:
            self.add_log("System", "没有可回退的快照。")
            return
        changed = self.snapshot.changes()
        ok, detail = self.snapshot.restore()
        if not ok:
            self.add_log("System", f"❌ {detail}")
            return
        for d in changed:
            self.editor.reload_path(d.abs_path)
        self.editor.clear_marks()
        self.project_tree.refresh()
        if act_id:
            self.chat_log.retire_actions(act_id, "↩ 已撤销这次修改")
        self.add_log("System", f"↩️ {detail}")

    def _render_ai_changes(self):
        """一轮结束后，把磁盘上真正发生的改动摆出来。

        故意不用模型 Edit 调用里报的 old/new：现算的是磁盘真实结果，
        模型一轮改三处也能一次展示完，说改了实际没改也瞒不过去。
        """
        if self.snapshot is None or not self.snapshot.has_snapshot:
            return
        changes = self.snapshot.changes()
        logger.info("这一轮磁盘上改了 {} 个文件：{}", len(changes),
                    [d.rel_path for d in changes])
        if not changes:
            return

        for d in changes:
            self.chat_log.add_diff(snapshot_mod.to_payload(d))

        # 编辑器跳到第一处改动并给改过的行铺底色
        first = changes[0]
        if first.abs_path:
            self.editor.goto_line(first.abs_path, first.first_line,
                                  snapshot_mod.added_lines(first))
            self.project_tree.reveal(first.abs_path)
        for d in changes[1:]:
            if d.abs_path:
                ed = self.editor.editor_for(d.abs_path)
                if ed:
                    ed.mark_changes(snapshot_mod.added_lines(d))

        self.project_tree.refresh()
        self._act_seq += 1
        names = "、".join(os.path.basename(d.rel_path) for d in changes[:3])
        self.chat_log.add_actions(
            f"act{self._act_seq}",
            f"✅ 已修改 <b>{len(changes)}</b> 个文件：{names}",
            "编译大约几秒钟。烧录前记得先把开关拨到 BOOT 端。",
        )

    # ---------- 高级模式课程流程 ----------

    @staticmethod
    def _make_separator() -> QFrame:
        line = QFrame()
        line.setObjectName("toolbar_sep")
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedWidth(1)
        return line

    def _update_lesson_nav(self):
        """课程导航只在高级模式出现，并处理首尾课的边界。"""
        advanced = self.current_difficulty == "高级"
        for w in (self.btn_lesson_prev, self.btn_lesson_next,
                  self.lbl_lesson, self.progress_bar):
            w.setVisible(advanced)
        if not advanced:
            return
        self.btn_lesson_prev.setEnabled(not self.lessons.at_start)
        self.btn_lesson_next.setEnabled(not self.lessons.at_end)
        self.btn_lesson_next.setText("🎉 已完成" if self.lessons.at_end else "下一步 ▶")
        self.lbl_lesson.setText(self.lessons.label)
        self.progress_bar.setValue(self.lessons.index + 1)

    def _render_current_lesson(self):
        """把当前课的正文原样渲染到对话区（不调用模型）。"""
        self._update_lesson_nav()
        self.add_log("课程", f"{self.lessons.header}\n\n{self.lessons.lesson['content']}")

    def go_prev_lesson(self):
        if self.lessons.prev():
            self._render_current_lesson()

    def go_next_lesson(self):
        if self.lessons.next():
            self._render_current_lesson()

    def _handle_lesson_command(self, text: str) -> bool:
        """是课程导航指令就执行并返回 True（不发给模型）。"""
        if self.current_difficulty != "高级":
            return False
        result = self.lessons.handle_command(text)
        if result == lesson_flow.MOVED:
            self._render_current_lesson()
        elif result == lesson_flow.AT_END:
            self.add_log("System", "已经是最后一课了 🎉")
        elif result == lesson_flow.AT_START:
            self.add_log("System", "已经是第一课了。")
        else:
            return False
        return True

    def check_save_button(self):
        self.btn_save.setEnabled(self.editor.is_dirty() and bool(self.project_root))

    def _on_editor_file_changed(self, _path):
        """当前文件由编辑器自己持有（editor.current_path），这里只刷新按钮态。"""
        self.check_save_button()

    # ---------- 工程与文件 ----------

    def open_project_folder(self):
        """打开一个工程目录。这是"当前工程"唯一的显式来源。"""
        start = self.project_root or load_workspace_config().get("workspace_dir", "")
        path = QFileDialog.getExistingDirectory(self, "打开 e2 studio 工程目录", start)
        if not path:
            return
        # 选到 src/ 这类子目录时向上找真正的工程根，省得学生重选
        if not project_context.is_project_root(path):
            up = project_context.walk_up_for_root(path)
            if up:
                path = up
        self.set_project_root(path)

    def _restore_last_project(self):
        """启动时恢复上次的工程，省得每次重开都要再点一遍。"""
        last = load_workspace_config().get("last_project", "")
        if last and os.path.isdir(last):
            self.set_project_root(last, quiet=True)

    def _confirm_dirty(self, title: str, consequence: str) -> bool:
        """有未保存的文件时先问一句。返回 False 表示调用方应当中止。

        三个入口都要问：切换工程、让 AI 改代码、编译。
        原因不一样但后果是同一类——**磁盘上的内容不是学生眼前看到的内容**：
          切工程  改动直接丢
          让 AI 改 AI 读的是磁盘上的旧代码，改完 reload 会盖掉手改的部分
          编译    编进固件的是磁盘上的旧代码，学生却以为编的是自己刚写的
        """
        dirty = self.editor.dirty_paths()
        if not dirty:
            return True
        names = "、".join(os.path.basename(p) for p in dirty[:5])
        logger.info("有未保存的文件 {}，询问学生（{}）", dirty, title)
        choice = QMessageBox.question(
            self, title, f"{names} 还没保存。\n{consequence}",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if choice == QMessageBox.StandardButton.Cancel:
            logger.info("学生选择取消")
            return False
        if choice == QMessageBox.StandardButton.Save:
            self.editor.save_all()
            logger.info("已保存后继续")
        return True

    def _confirm_close_project(self) -> bool:
        """关掉当前工程前处理未保存的文件。返回是否继续。"""
        return self._confirm_dirty("有未保存的改动", "切换工程会丢失这些改动。")

    def _apply_project_state(self):
        """没有打开工程时，把依赖工程的操作全部关掉。

        这样"当前工程"就不只是一个变量，而是界面上看得见的前置条件——
        学生不可能在没有工程的情况下误触编译或烧录。
        """
        has = bool(self.project_root)
        is_ra = has and project_context.is_project_root(self.project_root)
        for btn in (self.btn_build, self.btn_flash, self.btn_save):
            btn.setEnabled(has)
        self.btn_rasc.setEnabled(is_ra)
        if not has:
            self.editor.close_all()

    def set_project_root(self, path: str, quiet: bool = False):
        # 换工程要先收拾旧工程的标签页，否则两个工程的文件会混在一起
        if self.project_root and os.path.abspath(path) != os.path.abspath(self.project_root):
            if not self._confirm_close_project():
                return
            self.editor.close_all()

        is_ra = self.project_tree.set_root(path)
        self.project_root = path
        self._close_advisor()                    # 换工程要重开会话，旧会话锁在旧目录
        self._apply_project_state()

        name = os.path.basename(path.rstrip(os.sep)) or path
        if not quiet:
            if is_ra:
                self.add_log("System", f"📂 已打开工程 <b>{name}</b>")
            else:
                self.add_log("System",
                             f"📂 已打开 <b>{name}</b>，但里面没有 configuration.xml，"
                             f"可能不是 e2 studio 工程。")

        save_workspace_config(last_project=path)

        # 默认打开 hal_entry.c，学生一眼能看到入口
        entry = os.path.join(path, "src", "hal_entry.c")
        if os.path.isfile(entry):
            self.open_file_path(entry)

        # 初级模式提前把会话建起来：首轮冷启动要十几秒，等学生开口就晚了
        if self.current_difficulty == "初级":
            self._ensure_advisor()

    def open_file_path(self, path: str):
        """在编辑器里打开一个文件（已经开着就切过去）。"""
        if self.editor.open_file(path):
            self.project_tree.reveal(path)

    def save_file(self):
        path = self.editor.current_path
        if not path:
            self.add_log("System", "请先从左侧文件树里打开一个文件再保存。")
            return
        if self.editor.save_current():
            self.add_log("System", f"已保存: {os.path.basename(path)}")
        self.check_save_button()

    # ---------- 对话区 ----------
    # 渲染细节都在 chat_view.ChatView 里，这里只负责把消息投进去。

    def refresh_chat_display(self):
        """主题切换时调用——每条消息自己会重新上色，不用重建。"""
        self.chat_log.set_theme(self.current_theme)

    def add_log(self, role, text):
        """兼容原有调用点：'我' / 'System' / '课程' / 其它(=AI 完整回复)。"""
        if role in ("我", "学生"):
            self.chat_log.add_user(text)
        elif role == "System":
            self.chat_log.add_system(text)
        elif role == "课程":
            header, _, body = text.partition("\n\n")
            self.chat_log.add_lesson(header, body)
        else:
            self.last_ai_response = text
            self.btn_explain.setEnabled(True)
            bubble = self.chat_log.begin_assistant()
            bubble.append_text(text)
            bubble.finish()

    def start_chat(self):
        user_text = self.txt_input.text().strip()
        if not user_text:
            return

        # 高级模式下的"下一步/上一步"由程序处理，不消耗模型调用
        if self._handle_lesson_command(user_text):
            self.add_log("我", user_text)
            self.txt_input.clear()
            return

        self._ask_advisor(user_text)

    # ---------- agent 会话（两个模式共用一套管道） ----------

    def _ask_advisor(self, user_text):
        """把问题交给常驻的 agent 会话，它能自己读学生的工程。"""
        if not self._ensure_advisor():
            return

        # AI 读的、改的都是磁盘上的文件，编辑器里没保存的部分它看不见，
        # 而且它改完之后 reload_path 会把学生手改的内容盖掉
        if not self._confirm_dirty(
                "有未保存的改动",
                "AI 看不到编辑器里没保存的内容，改完还会覆盖掉它们。"):
            return

        self.add_log("我", user_text)
        self.txt_input.clear()

        if self.current_difficulty == "初级":
            # AI 动手前先拍快照。拍不成就不许它改——没有退路的改动不能做
            self.snapshot = snapshot_mod.SrcSnapshot(self.project_root)
            if not self.snapshot.take():
                self.snapshot = None
                self.add_log("System",
                             "❌ 没能给 src/ 做备份，为安全起见这次不改代码。"
                             "请确认工程里有 src/ 目录且没有被占用。")
                return
            self.editor.clear_marks()
            self._lock_send("AI 正在读你的代码...")
        else:
            self._lock_send("AI 导师正在查看你的工程...")

        self._bubble = self.chat_log.begin_assistant()
        # 课程前言只属于高级模式。初级模式带上它的话，每个"让小马前进"
        # 前面都会顶着一整课的正文，模型既跑偏又变慢
        preamble = self._lesson_preamble() if self.current_difficulty == "高级" else ""
        self.advisor.ask(preamble + user_text)

    def _ensure_advisor(self) -> bool:
        """需要时开一条会话；工程找不到就拒绝启动并说明原因。

        两个模式的权限完全不同，所以换模式必须重开会话（``_advisor_mode``）。
        """
        mode = self.current_difficulty
        if (self.advisor is not None and self.advisor.isRunning()
                and self._advisor_mode == mode):
            return True
        if self.advisor is not None:
            logger.info("模式从 {} 换成 {}，重开会话", self._advisor_mode, mode)
            self._close_advisor()

        root = self.project_root
        if not root:
            self.add_log("System",
                         "还没打开工程，AI 无法查看你的代码。<br>"
                         "请先点左上角【📂 打开工程】。")
            return False

        if mode == "初级":
            server, compile_tool = make_compile_server(root)
            cfg = AdvisorConfig(
                project_root=root,
                system_prompt=self._beginner_system_prompt(root),
                base_url=get_anthropic_base_url(),    # 注意：不是 OpenAI 那个 /v1
                api_key=self.user_api_key or get_api_key(),
                model=get_edit_model(),
                allowed_tools=EDIT_TOOLS + [compile_tool],
                write_roots=[os.path.join(root, "src")],
                mcp_servers={"horse": server},
                # 换成 opus 时一轮改码实测 $0.4 上下，默认的 0.5 只够一轮
                # 就被掐断，所以放宽；haiku 下这个上限碰不到
                max_budget_usd=8.0,
            )
            note = "（AI 只能改 src/ 下的代码，每次改动都可以一键撤销）"
        else:
            # 高级模式同样给编译工具：它改不了文件，但能自己编一遍看到真实
            # 报错，省掉"学生复述编译错误"这一环——初学者抄错行号、漏掉关键
            # 那一条是常事。编译不产出代码，不违反"不给完整代码"的教学原则。
            server, compile_tool = make_compile_server(root)
            cfg = AdvisorConfig(
                project_root=root,
                system_prompt=self._advisor_system_prompt(root),
                base_url=get_anthropic_base_url(),
                api_key=self.user_api_key or get_api_key(),
                model=get_agent_model(),
                allowed_tools=READONLY_TOOLS + [compile_tool],   # 只读 + 编译
                mcp_servers={"horse": server},
            )
            note = "（AI 只读，不会修改文件）"

        self.advisor = Advisor(cfg, parent=self)
        self._advisor_mode = mode
        self.advisor.text.connect(self._on_advisor_text)
        self.advisor.tool.connect(self._on_advisor_tool)
        self.advisor.edited.connect(self._on_advisor_edited)
        self.advisor.denied.connect(self._on_advisor_denied)
        self.advisor.thinking.connect(self._on_advisor_thinking)
        self.advisor.turn_done.connect(self._on_advisor_done)
        self.advisor.failed.connect(self._on_advisor_failed)
        self.advisor.start()
        self.add_log("System", f"已连接工程：{os.path.basename(root)}{note}")
        return True

    def _advisor_system_prompt(self, root) -> str:
        """角色设定 + 工程说明。**不含课程正文**——课程随消息走，
        这样 system prompt 恒定，会话缓存不会因为换课而失效。"""
        return (ADVISOR_ROLE_PROMPT + "\n\n【学生的工程】\n"
                + project_context.describe(root))

    def _beginner_system_prompt(self, root) -> str:
        """初级模式：角色 + 工程结构 + 从 src/ 现读出来的接口清单。

        接口清单不手写：队友改了代码手写的就过时了，而模型照着过时的清单
        去改会改错。这里全部从磁盘现读，永远和代码一致。
        """
        return (BEGINNER_AGENT_PROMPT
                + "\n\n【学生的工程】\n" + project_context.describe(root)
                + "\n\n【这台小马现有的接口】\n" + project_api.describe_api(root))

    def _on_advisor_text(self, chunk):
        if self._bubble:
            self._bubble.append_text(chunk)
            self.chat_log.scroll_to_bottom()

    def _on_advisor_tool(self, icon, name, detail):
        if self._bubble:
            self._bubble.add_tool(name, detail, icon)
            self.chat_log.scroll_to_bottom()

    def _on_advisor_edited(self, path):
        """AI 刚改了一个文件。已经开着的标签立刻重读，让代码在眼前变。"""
        self.editor.reload_path(path)

    def _on_advisor_denied(self, name, reason):
        if self._bubble:
            self._bubble.add_denied(name, reason)

    def _on_advisor_thinking(self):
        if self._bubble:
            self._bubble.set_status("思考中…")

    def _on_advisor_done(self, summary):
        logger.info("一轮结束（{}），开始渲染改动", summary or "无用量信息")
        if self._bubble:
            self._bubble.finish(summary)
            self.last_ai_response = self._bubble.raw_text
            self.btn_explain.setEnabled(True)
            self._bubble = None
        if self.current_difficulty == "初级":
            self._render_ai_changes()
        self._unlock_send()

    def _on_advisor_failed(self, message):
        logger.error("agent 报错：{}", message)
        if self._bubble:
            self._bubble.finish()
            self._bubble = None
        self.add_log("System", f"AI 出错：{message}")
        self._unlock_send()

    def _lesson_preamble(self) -> str:
        """课程变了就在下一个问题前面带一段说明，之后就不再重复。

        不为换课单独发一次请求：学生连点几下【下一步】会排出一串空转的
        回合，把他真正的提问堵在后面。附在问题前面则是零额外调用。
        """
        if self._lesson_synced == self.lessons.index:
            return ""
        self._lesson_synced = self.lessons.index
        lesson = self.lessons.lesson
        return (
            f"[课程上下文] 学生现在在 {self.lessons.header}。以下是他屏幕上看到的正文，"
            f"你答疑时以它为准，但不要复述：\n\n{lesson['content']}\n\n"
            f"本课教学重点：{lesson.get('guide', '')}\n\n"
            f"[学生的问题] "
        )

    # ---------- 发送锁 ----------

    def _lock_send(self, message):
        """锁住输入，并开一个每秒跳字的计时器。

        模型在思考或者在憋一个很长的 Edit 入参时，界面上**什么都不会动**
        （流式事件要等整个 block 结束才来），看着就像死了。状态栏一直在跳
        秒数至少能说明它还活着，也方便对着日志算时间。
        """
        self._turn_started = time.monotonic()
        self._turn_hint = message
        self.status_bar.showMessage(message)
        self.btn_send.setEnabled(False)
        self.txt_input.setEnabled(False)
        # 难度下拉框一起锁上。切模式要重开会话，而正在跑的这一轮是停不下来的
        # （见 Advisor.shutdown），初级模式下它甚至还在改文件——让它跑完再切。
        self.difficulty_combo.setEnabled(False)
        self._turn_timer.start(1000)

    def _tick_turn(self):
        elapsed = time.monotonic() - self._turn_started
        self.status_bar.showMessage(f"{self._turn_hint}（已等待 {elapsed:.0f} 秒）")
        if elapsed > 90 and int(elapsed) % 30 == 0:
            logger.warning("这一轮已经等了 {:.0f} 秒还没结束", elapsed)

    def _unlock_send(self):
        self._turn_timer.stop()
        self.status_bar.clearMessage()
        self.btn_send.setEnabled(True)
        self.txt_input.setEnabled(True)
        self.difficulty_combo.setEnabled(True)
        self.txt_input.setFocus()

    def explain_concept(self):
        if not self.last_ai_response:
            return
        self.status_bar.showMessage("正在抽取关联核心技术...")

        explain_prompt = f"""
你是一位生动有趣的嵌入式硬件科普老师。
用户正在学习瑞萨 RA4M2 机器马开发，并点击了"知识详解"。
刚才导师（你）对用户指导的内容是：
"{self.last_ai_response}"

【专属重点知识库（对应教程黄框内容）】
请根据导师刚才说的话，自动识别当前处于哪个开发步骤，并详细讲解以下列表中对应的核心知识点（只讲当前步骤涉及的，不要全讲！）：
**工程与时钟树**：什么是 FSP？晶振 (XTAL) 是什么？PLL (锁相环) 倍频的作用是什么？
**调试引脚**：什么是 SWD (Serial Wire Debug) 模式？它需要哪几根线？
**定时器与 PWM**：什么是 PWM 的占空比 (Duty Cycle)？50Hz 的频率代表什么？它是如何控制机器马腿部（舵机/电机）转动角度的？
**串口 (UART)**：UART 通信原理是什么？波特率 9600 是什么意思？单片机里的"回调函数 (Callback)"是用来干嘛的？
**I2C 总线**：I2C 通信的 SCL (时钟线) 和 SDA (数据线) 分别负责什么？主从机通信机制是怎样的？
**OLED 与取模**：单片机为什么不直接显示图片，而是需要"字模"和"图像取模"？取模软件里的阴码/阳码、逆向是什么原理？
**编译与烧录**：编译生成的 .hex 文件本质是什么？烧录 (Program) 动作是如何把代码固化到单片机芯片内部的？

【输出要求】
- 必须使用 Markdown 排版，使用加粗和分点。
- 语言通俗易懂，尽量用生活中的例子打比方。
- **绝对不要写代码**，只讲硬件原理和核心概念。
"""

        messages = [{"role": "user", "content": explain_prompt}]
        model = self.user_endpoint_id or get_endpoint_id()
        self.worker_explain = AIWorker(self.client, messages, req_type="concept", model=model)
        self.worker_explain.response_received.connect(self.on_ai_reply)
        self.worker_explain.start()

    def on_ai_reply(self, reply, success, req_type):
        self.btn_send.setEnabled(True)
        self.status_bar.clearMessage()

        if not success:
            self.add_log("System", reply)
            return

        if req_type == "concept":
            dialog = ConceptDialog("知识点深入解析", reply, self)
            dialog.exec()
            return

        if req_type == "chat":
            self.history.append({"role": "assistant", "content": reply})

        if reply.strip():
            self.add_log("导师", reply.strip())

    def _close_advisor(self):
        """结束 agent 会话（切模式、换工程、退出时）。"""
        if self.advisor is not None:
            self.advisor.shutdown()
            self.advisor = None
        self._advisor_mode = ""
        self._bubble = None
        self._lesson_synced = -1

    def closeEvent(self, event):
        if not self._confirm_close_project():
            event.ignore()
            return
        self._close_advisor()
        super().closeEvent(event)
