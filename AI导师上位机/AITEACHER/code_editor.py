"""代码编辑区：带语法高亮的编辑器 + 多文件标签页。

原来是一个裸 QTextEdit：没有语法高亮、没有行号，而且一次只能开一个文件——
点树里另一个文件会直接顶掉当前内容，改了没保存就丢了。

QScintilla 是 SciTE / Notepad++ 的内核，C 词法器、行号边栏、当前行高亮、
括号匹配、自动缩进都是内置的，不用自己画。
"""

import os

from PyQt6.Qsci import QsciLexerCPP, QsciScintilla
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFrame, QLabel, QMessageBox, QStackedWidget,
                             QTabWidget, QVBoxLayout, QWidget)

# 明暗两套配色。键名对应 QsciLexerCPP 的 token 类型。
THEMES = {
    "dark": dict(
        paper="#1e1e1e", text="#d4d4d4", margin_bg="#1e1e1e", margin_fg="#6a6a6a",
        caret_line="#2a2a2e", caret="#ffffff", selection="#264f78",
        change_mark="#1d3326", error_mark="#3d1d20",
        keyword="#569cd6", comment="#6a9955", string="#ce9178", number="#b5cea8",
        preproc="#c586c0", operator="#d4d4d4", identifier="#9cdcfe",
        brace_ok="#ffd700", brace_bad="#ff5555",
    ),
    "light": dict(
        paper="#ffffff", text="#24292e", margin_bg="#f6f8fa", margin_fg="#9aa0a6",
        caret_line="#f2f4f7", caret="#000000", selection="#cfe3ff",
        change_mark="#d6f5e0", error_mark="#ffe3e0",
        keyword="#0000ff", comment="#008000", string="#a31515", number="#098658",
        preproc="#af00db", operator="#24292e", identifier="#001080",
        brace_ok="#0a7d00", brace_bad="#d10000",
    ),
}


def _mono_font(size: int = 12) -> QFont:
    f = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    for name in ("Cascadia Mono", "Consolas", "JetBrains Mono", "Fira Code",
                 "DejaVu Sans Mono", "Menlo"):
        candidate = QFont(name)
        if QFontDatabase.families().count(name):
            f = candidate
            break
    f.setPointSize(size)
    f.setFixedPitch(True)
    return f


class CodeEditor(QsciScintilla):
    """单个文件的编辑器。"""

    CHANGE_MARKER = 8       # 0-7 被 QScintilla 的折叠边栏占着
    ERROR_MARKER = 9        # 编译报错的行

    def __init__(self, path: str = "", theme: str = "dark", parent=None):
        super().__init__(parent)
        self.path = path
        self._theme = theme
        # 自己记一份标记行号：setText() 会把 Scintilla 里的 marker 全清掉，
        # 重新读盘之后要照着这份补回来
        self._marks = {self.CHANGE_MARKER: [], self.ERROR_MARKER: []}

        # 必须自己留一份：应用的全局 QSS 里有 font-family 规则，QSS 的优先级
        # 高于 setFont()，读回 self.font() 拿到的是被覆盖后的界面字体
        # （Segoe UI / pointSize=-1），拿它去设词法器会让行高塌成 3px。
        self._font = _mono_font()
        font = self._font
        self.setFont(font)
        self.setUtf8(True)
        self.setEolMode(QsciScintilla.EolMode.EolWindows)   # RA 工程里的源码是 CRLF
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setAutoIndent(True)
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginLineNumbers(0, True)
        self.setCaretLineVisible(True)
        # 当前行画成一圈细边框而不是填充底色。填充的话会盖住这一行的
        # marker——从问题列表双击跳过去，恰恰是那一行的红底看不见了。
        self.SendScintilla(QsciScintilla.SCI_SETCARETLINEFRAME, 2)
        self.setScrollWidth(1)                              # 让横向滚动条按内容自适应
        self.setScrollWidthTracking(True)
        # QsciScintilla 是 QAbstractScrollArea：默认带一圈边框，两条滚动条
        # 交汇处还有一块 corner。这两处不归 Scintilla 的 setPaper 管，跟的是
        # 控件调色板，不设就是系统默认（亮色模式下看着像黑框 + 黑方块）。
        self.setFrameShape(QFrame.Shape.NoFrame)
        # AI 改过的行整行铺一层底色，学生一眼看得出动了哪里
        self.markerDefine(QsciScintilla.MarkerSymbol.Background, self.CHANGE_MARKER)
        self.markerDefine(QsciScintilla.MarkerSymbol.Background, self.ERROR_MARKER)

        lexer = QsciLexerCPP(self)
        lexer.setFont(font)
        self.setLexer(lexer)
        self._lexer = lexer

        self.apply_theme(theme)

    # ---- 主题 ----

    def apply_theme(self, theme: str):
        self._theme = theme if theme in THEMES else "dark"
        c = THEMES[self._theme]
        lex, font = self._lexer, self._font

        lex.setDefaultPaper(QColor(c["paper"]))
        lex.setDefaultColor(QColor(c["text"]))
        for style in range(128):
            lex.setPaper(QColor(c["paper"]), style)
            lex.setFont(font, style)

        S = QsciLexerCPP
        colors = {
            S.Default: c["text"], S.Identifier: c["identifier"],
            S.Keyword: c["keyword"], S.KeywordSet2: c["keyword"],
            S.Comment: c["comment"], S.CommentLine: c["comment"],
            S.CommentDoc: c["comment"], S.CommentLineDoc: c["comment"],
            S.DoubleQuotedString: c["string"], S.SingleQuotedString: c["string"],
            S.RawString: c["string"], S.Number: c["number"],
            S.PreProcessor: c["preproc"], S.PreProcessorComment: c["comment"],
            S.Operator: c["operator"], S.GlobalClass: c["identifier"],
        }
        for style, color in colors.items():
            lex.setColor(QColor(color), style)

        self.setMarginsBackgroundColor(QColor(c["margin_bg"]))
        self.setMarginsForegroundColor(QColor(c["margin_fg"]))
        self.setCaretLineBackgroundColor(QColor(c["caret_line"]))
        self.setCaretForegroundColor(QColor(c["caret"]))
        self.setSelectionBackgroundColor(QColor(c["selection"]))
        self.setMatchedBraceForegroundColor(QColor(c["brace_ok"]))
        self.setUnmatchedBraceForegroundColor(QColor(c["brace_bad"]))
        self.setMarginWidth(0, "0000")
        self.setPaper(QColor(c["paper"]))
        self.setColor(QColor(c["text"]))

        self.setMarkerBackgroundColor(QColor(c["change_mark"]), self.CHANGE_MARKER)
        self.setMarkerBackgroundColor(QColor(c["error_mark"]), self.ERROR_MARKER)

        # 滚动条交汇处那块 corner 由样式按 Window 角色画，跟着边栏底色走
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor(c["paper"]))
        pal.setColor(QPalette.ColorRole.Window, QColor(c["margin_bg"]))
        self.setPalette(pal)

    # ---- AI 改动标记 ----

    def mark_changes(self, lines):
        """给这些行（1 起）铺"AI 改过"的底色；传空清掉。"""
        self._set_marker(self.CHANGE_MARKER, lines)

    def mark_errors(self, lines):
        """给这些行铺"编译报错"的底色；传空清掉。"""
        self._set_marker(self.ERROR_MARKER, lines)

    def _set_marker(self, marker, lines):
        self._marks[marker] = list(lines)
        self.markerDeleteAll(marker)
        for line in lines:
            if 1 <= line <= self.lines():
                self.markerAdd(line - 1, marker)

    def restore_marks(self):
        """重新读盘之后把标记补回来。"""
        for marker, lines in self._marks.items():
            self.markerDeleteAll(marker)
            for line in lines:
                if 1 <= line <= self.lines():
                    self.markerAdd(line - 1, marker)


class EditorTabs(QWidget):
    """多文件标签页。没有打开文件时显示一句提示。"""

    dirty_changed = pyqtSignal(bool)        # 当前文件有没有未保存的改动
    current_file_changed = pyqtSignal(str)  # 切换标签或打开新文件

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        self._editors: dict[str, CodeEditor] = {}
        # 编译错误按文件记着：报错的文件很可能还没打开，等它被打开时再补红底
        self._errors: dict[str, list] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)
        self._empty = QLabel("请先点左上角【📂 打开工程】，再从左侧文件树里打开文件")
        self._empty.setObjectName("editor_empty")
        self._empty.setWordWrap(True)
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._tabs = QTabWidget(self)
        self._tabs.setObjectName("editor_tabs")
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.setDocumentMode(True)
        self._tabs.tabCloseRequested.connect(self._close_tab)
        self._tabs.currentChanged.connect(self._on_tab_changed)

        self._stack.addWidget(self._empty)
        self._stack.addWidget(self._tabs)
        lay.addWidget(self._stack)
        self._sync_stack()

    # ---- 查询 ----

    @property
    def current_path(self) -> str:
        ed = self._tabs.currentWidget()
        return ed.path if isinstance(ed, CodeEditor) else ""

    @property
    def has_files(self) -> bool:
        return self._tabs.count() > 0

    def current_text(self) -> str:
        ed = self._tabs.currentWidget()
        return ed.text() if isinstance(ed, CodeEditor) else ""

    def is_dirty(self, path: str = "") -> bool:
        ed = self._editors.get(path) if path else self._tabs.currentWidget()
        return bool(isinstance(ed, CodeEditor) and ed.isModified())

    def dirty_paths(self) -> list[str]:
        return [p for p, e in self._editors.items() if e.isModified()]

    # ---- 打开 / 关闭 ----

    def open_file(self, path: str) -> bool:
        if not path or not os.path.isfile(path):
            return False
        path = os.path.abspath(path)
        if path in self._editors:                     # 已经开着就切过去
            self._tabs.setCurrentWidget(self._editors[path])
            return True
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="gbk", errors="replace", newline="") as f:
                content = f.read()
        except OSError as e:
            QMessageBox.warning(self, "打开失败", str(e))
            return False

        ed = CodeEditor(path, self._theme, self)
        ed.setText(content)
        ed.setModified(False)
        ed.mark_errors(self._errors.get(path, []))
        ed.modificationChanged.connect(lambda _m, p=path: self._on_modified(p))
        self._editors[path] = ed
        idx = self._tabs.addTab(ed, os.path.basename(path))
        self._tabs.setTabToolTip(idx, path)
        self._install_close_button(idx)
        self._tabs.setCurrentIndex(idx)
        self._sync_stack()
        return True

    def close_all(self):
        for ed in list(self._editors.values()):
            ed.deleteLater()
        self._editors.clear()
        self._tabs.clear()
        self._sync_stack()
        self.current_file_changed.emit("")
        self.dirty_changed.emit(False)

    def _close_tab(self, index: int):
        ed = self._tabs.widget(index)
        if not isinstance(ed, CodeEditor):
            return
        if ed.isModified() and not self._confirm_discard(ed):
            return
        self._editors.pop(ed.path, None)
        self._tabs.removeTab(index)
        ed.deleteLater()
        self._sync_stack()

    def _confirm_discard(self, ed: CodeEditor) -> bool:
        name = os.path.basename(ed.path)
        choice = QMessageBox.question(
            self, "未保存的改动", f"{name} 有未保存的改动，确定关闭吗？",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Save:
            return self.save_path(ed.path)
        return True

    # ---- 保存 ----

    def save_current(self) -> bool:
        return self.save_path(self.current_path)

    def save_path(self, path: str) -> bool:
        ed = self._editors.get(path)
        if not ed:
            return False
        try:
            # newline="" + 编辑器用 CRLF：写回去和 e2 studio 的换行风格一致，
            # 否则每保存一次整个文件都会显示成被改过
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(ed.text())
        except OSError as e:
            QMessageBox.warning(self, "保存失败", str(e))
            return False
        ed.setModified(False)
        self._refresh_tab_title(path)
        return True

    def save_all(self) -> int:
        return sum(1 for p in self.dirty_paths() if self.save_path(p))

    def reload_path(self, path: str):
        """外部（比如 AI）改过文件后重新读盘。"""
        ed = self._editors.get(os.path.abspath(path))
        if not ed:
            return
        try:
            with open(ed.path, "r", encoding="utf-8", newline="") as f:
                content = f.read()
        except OSError:
            return
        line, col = ed.getCursorPosition()
        ed.setText(content)
        ed.setModified(False)
        ed.setCursorPosition(min(line, ed.lines() - 1), col)
        ed.restore_marks()
        self._refresh_tab_title(ed.path)

    def goto_line(self, path: str, line: int, mark_lines=None):
        """打开文件并跳到某一行，可选地给若干行铺上"AI 改过"的底色。"""
        if not self.open_file(path):
            return False
        ed = self._editors.get(os.path.abspath(path))
        if not ed:
            return False
        self.reload_path(path)
        line = max(1, min(line, ed.lines()))
        # mark_lines=None 表示"只跳转，别动已有的标记"——从问题列表双击进来
        # 就是这种情况，不然会把编译错误的红底和 AI 改动的绿底一起抹掉
        if mark_lines is not None:
            ed.mark_changes(mark_lines)
        ed.setCursorPosition(line - 1, 0)
        # 先滚到目标行下面几行再滚回来，让改动落在视野中部而不是贴底
        ed.ensureLineVisible(min(ed.lines() - 1, line + 6))
        ed.ensureLineVisible(max(0, line - 4))
        ed.setFocus()
        return True

    def clear_marks(self):
        for ed in self._editors.values():
            ed.mark_changes([])

    def set_errors(self, by_path: dict):
        """{绝对路径: [行号]}。没在字典里的文件会被清掉红底。

        记下来而不是只作用于当前打开的标签——报错的文件多半还没打开，
        学生从问题列表双击进去的时候才需要那个红底。
        """
        self._errors = {os.path.abspath(p): list(v) for p, v in by_path.items()}
        for path, ed in self._editors.items():
            ed.mark_errors(self._errors.get(path, []))

    def editor_for(self, path: str):
        """已经打开的话返回那个编辑器，否则 None。"""
        return self._editors.get(os.path.abspath(path))

    # ---- 主题 ----

    def set_theme(self, theme: str):
        self._theme = theme
        for ed in self._editors.values():
            ed.apply_theme(theme)

    # ---- 内部 ----

    def _install_close_button(self, index: int):
        """用自己的按钮替掉系统那个红叉，才能跟着主题走。"""
        from PyQt6.QtWidgets import QPushButton, QTabBar
        btn = QPushButton("✕")
        btn.setObjectName("tab_close")
        btn.setFixedSize(16, 16)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self._close_by_widget(self._tabs.widget(
            self._tabs.tabBar().tabAt(btn.mapTo(self._tabs.tabBar(), btn.rect().center())))))
        self._tabs.tabBar().setTabButton(index, QTabBar.ButtonPosition.RightSide, btn)

    def _close_by_widget(self, widget):
        idx = self._tabs.indexOf(widget)
        if idx >= 0:
            self._close_tab(idx)

    def _sync_stack(self):
        self._stack.setCurrentWidget(self._tabs if self.has_files else self._empty)

    def _refresh_tab_title(self, path: str):
        ed = self._editors.get(path)
        if not ed:
            return
        idx = self._tabs.indexOf(ed)
        if idx >= 0:
            mark = " ●" if ed.isModified() else ""
            self._tabs.setTabText(idx, os.path.basename(path) + mark)

    def _on_modified(self, path: str):
        self._refresh_tab_title(path)
        if path == self.current_path:
            self.dirty_changed.emit(self.is_dirty())

    def _on_tab_changed(self, _index: int):
        self.current_file_changed.emit(self.current_path)
        self.dirty_changed.emit(self.is_dirty())
