"""编辑器下面那块输出面板：编译日志 + 可双击跳转的问题列表。

以前编译日志是一行行灌进对话区的，几十行 ``arm-none-eabi-objcopy ...``
把对话挤没了，而且选不中、更点不动。挪到这里之后对话区只留三行结论。

问题列表双击 → 跳到出错那一行。这是演示时真会用到的：AI 改错了、编译红了，
双击直接落到出错的地方。
"""

import os

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                             QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

# 日志里这些字样标红/标黄，一眼能看出哪行是重点
_BAD = ("error:", "Error ", "fatal error", "❌", "undefined reference")
_WARN = ("warning:", "⚠")
# 这些是过程噪音，压暗
_DIM = ("Building file:", "Building target:", "工具链:", "已清除旧固件",
        "Invoking:", "Finished building")


def _mono_font(size: int = 11) -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    for name in ("Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono"):
        if QFontDatabase.families().count(name):
            f = QFont(name)
            break
    f.setPointSize(size)
    f.setFixedPitch(True)
    return f


class OutputPanel(QWidget):
    """两个标签页：编译输出 / 问题。

    信号：
        problem_activated(abs_path, line)   双击了一条问题
        closed()                            点了右上角的收起
    """

    problem_activated = pyqtSignal(str, int)
    closed = pyqtSignal()

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("output_panel")

        self.tabs = QTabWidget()
        self.tabs.setObjectName("output_tabs")

        self.log = QPlainTextEdit()
        self.log.setObjectName("output_log")
        self.log.setReadOnly(True)
        self.log.setFont(_mono_font())
        self.log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log.setMaximumBlockCount(4000)   # 全量重编几千行，别让它无限涨

        self.problems = QTreeWidget()
        self.problems.setObjectName("problem_list")
        self.problems.setColumnCount(2)
        self.problems.setHeaderLabels(["位置", "说明"])
        self.problems.setRootIsDecorated(False)
        self.problems.setUniformRowHeights(True)
        self.problems.itemActivated.connect(self._emit_problem)
        self.problems.itemDoubleClicked.connect(self._emit_problem)
        self.problems.setColumnWidth(0, 210)

        self.tabs.addTab(self.log, "编译输出")
        self.tabs.addTab(self.problems, "问题")

        # 标签栏右边塞一个收起按钮
        corner = QWidget()
        corner_lay = QHBoxLayout(corner)
        corner_lay.setContentsMargins(0, 0, 6, 0)
        corner_lay.setSpacing(6)
        self.lbl_summary = QLabel("")
        self.lbl_summary.setObjectName("output_summary")
        btn_close = QPushButton("✕")
        btn_close.setObjectName("output_close")
        btn_close.setFixedSize(20, 20)
        btn_close.setToolTip("收起输出面板")
        btn_close.clicked.connect(self.closed)
        corner_lay.addWidget(self.lbl_summary)
        corner_lay.addWidget(btn_close)
        self.tabs.setCornerWidget(corner, Qt.Corner.TopRightCorner)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.tabs)

        self.apply_theme(theme)

    # ---- 内容 ----

    def start_run(self, title: str):
        """开一次新的编译：清空、切到日志页。"""
        self.log.clear()
        self.problems.clear()
        self.lbl_summary.setText("")
        self.tabs.setTabText(1, "问题")
        self.tabs.setCurrentIndex(0)
        self.append(title)

    def append(self, line: str):
        self.log.appendHtml(self._colorize(line))
        self._to_bottom()

    def append_result(self, message: str, ok: bool):
        """最后那句结论。加粗 + 上色，暗色底下不能和一堆灰日志一个颜色。"""
        color = self._c("ok") if ok else self._c("bad")
        safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.log.appendHtml(
            f'<span style="color:{color}; font-weight:700; white-space:pre;">'
            f'{"✅" if ok else "❌"} {safe}</span>')
        self._to_bottom()

    def _to_bottom(self):
        self.log.verticalScrollBar().setValue(
            self.log.verticalScrollBar().maximum())

    def set_problems(self, diagnostics: list):
        """diagnostics 是 builder.parse_diagnostics() 的输出。"""
        self.problems.clear()
        errors = 0
        for d in diagnostics:
            bad = d["kind"] != "warning"
            errors += bad
            item = QTreeWidgetItem([
                f'{"❌" if bad else "⚠️"} {d["file"]}:{d["line"]}',
                d["message"],
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, (d["abs_path"], d["line"]))
            item.setForeground(0, QColor(self._c("bad") if bad else self._c("warn")))
            self.problems.addTopLevelItem(item)
        total = len(diagnostics)
        self.tabs.setTabText(1, f"问题 ({total})" if total else "问题")
        if errors:
            self.tabs.setCurrentIndex(1)      # 有错就直接把问题页顶到前面

    def set_summary(self, text: str, ok: bool):
        self.lbl_summary.setText(text)
        self.lbl_summary.setStyleSheet(
            f"color:{self._c('ok') if ok else self._c('bad')}; font-size:12px;")

    def _emit_problem(self, item, _col=0):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data[0] and os.path.isfile(data[0]):
            self.problem_activated.emit(data[0], int(data[1]))

    # ---- 主题 ----

    # 暗色的 fg 要够亮：一屏几十行编译日志，灰一点就整片糊。
    # dim 是给"这行不重要"用的（工具链路径、Building file 之类）。
    _PALETTE = {
        "dark": dict(fg="#e8e8ec", dim="#9aa0a6", bad="#ff6b61",
                     warn="#e3b341", ok="#4ade80"),
        "light": dict(fg="#24292e", dim="#7a7f87", bad="#cf222e",
                      warn="#9a6700", ok="#1a7f37"),
    }

    def _c(self, key):
        return self._PALETTE.get(self._theme, self._PALETTE["dark"])[key]

    def _colorize(self, line: str) -> str:
        safe = (line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        if any(k in line for k in _BAD):
            color = self._c("bad")
        elif any(k in line for k in _WARN):
            color = self._c("warn")
        elif any(k in line for k in _DIM):
            color = self._c("dim")     # 噪音行压暗，让报错更跳
        else:
            color = self._c("fg")
        return f'<span style="color:{color}; white-space:pre;">{safe}</span>'

    def apply_theme(self, theme: str):
        self._theme = theme if theme in self._PALETTE else "dark"
        self.problems.setColumnWidth(0, 210)
