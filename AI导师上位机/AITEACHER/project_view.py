"""工程文件树。

打开一个工程目录之后，"学生在做哪个工程"这件事就有了唯一答案，不用再
从编译设置、上次打开的工程、当前文件里三处猜。

RA 工程里 ra/fsp 有几千个文件，所以：
  - 用名字过滤只显示源码和配置（QFileSystemModel 是懒加载，不会一次扫全盘）
  - 默认只展开 src/，那是学生真正会动的地方
"""

import os
import shutil

from PyQt6.QtCore import QDir, QProcess, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFileSystemModel
from PyQt6.QtWidgets import (QAbstractItemView, QHBoxLayout, QInputDialog,
                             QLabel, QMenu, QMessageBox, QTreeView,
                             QVBoxLayout, QWidget)
from loguru import logger

import project_context


def _terminal_candidates():
    """按"越靠前越接近用户自己的默认终端"排出候选 (程序, 参数)。

    Linux 上没有一个所有发行版都认的"默认终端"，能用的约定有三条，依次是：
      1. ``$TERMINAL`` —— 用户自己指定的，最权威
      2. ``xdg-terminal-exec`` —— freedesktop 的终端规范，新版 xdg-utils 带
      3. ``x-terminal-emulator`` —— Debian/Ubuntu 的 alternatives 机制
    都没有再退回常见终端的硬列表。

    Windows 上直接起 cmd.exe 就行：Win11 会用系统设置里的"默认终端应用"
    来承载它（装了 Windows Terminal 就开在 Windows Terminal 里）。
    """
    if os.name == "nt":
        return [("cmd.exe", ["/K", "cd /d %CD%"])]
    env = os.environ.get("TERMINAL", "").strip()
    out = []
    if env:
        out.append((env, []))
    out += [("xdg-terminal-exec", []), ("x-terminal-emulator", [])]
    out += [(t, []) for t in ("ghostty", "wezterm", "kitty", "alacritty", "foot",
                              "konsole", "gnome-terminal", "xfce4-terminal",
                              "tilix", "terminator", "urxvt", "st", "xterm")]
    return out

# 学生会打开的文件类型；其余（.o/.d/.map/.elf）不显示
VISIBLE_PATTERNS = ["*.c", "*.h", "*.cpp", "*.hpp", "*.xml", "*.ld", "*.md", "*.txt"]


class ProjectTree(QWidget):
    """工程目录树。双击（或单击）文件时发出 file_activated。"""

    file_activated = pyqtSignal(str)
    file_created = pyqtSignal(str)     # 新建后由 UI 决定要不要打开它

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        head = QHBoxLayout()
        head.setContentsMargins(2, 0, 2, 0)
        self._title = QLabel("📂 未打开工程")
        self._title.setObjectName("tree_title")
        head.addWidget(self._title)
        head.addStretch()
        lay.addLayout(head)

        self._model = QFileSystemModel(self)
        self._model.setNameFilters(VISIBLE_PATTERNS)
        self._model.setNameFilterDisables(False)      # 不匹配的直接隐藏而不是置灰
        self._model.setFilter(QDir.Filter.AllDirs | QDir.Filter.Files
                              | QDir.Filter.NoDotAndDotDot)

        self._tree = QTreeView(self)
        self._tree.setObjectName("project_tree")
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setAnimated(True)
        self._tree.setIndentation(14)
        for col in (1, 2, 3):                          # 只留文件名列
            self._tree.hideColumn(col)
        self._tree.activated.connect(self._on_activated)
        self._tree.clicked.connect(self._on_activated)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._menu)
        lay.addWidget(self._tree)

    # ---- 对外 ----

    @property
    def root(self) -> str:
        return self._root

    def set_root(self, path: str) -> bool:
        """指向一个工程目录。返回它是不是合法的 RA 工程。"""
        if not path or not os.path.isdir(path):
            return False
        self._root = path
        self._model.setRootPath(path)
        self._tree.setRootIndex(self._model.index(path))
        name = os.path.basename(path.rstrip(os.sep)) or path
        ok = project_context.is_project_root(path)
        self._title.setText(("📂 " if ok else "⚠️ ") + name)
        self._title.setToolTip(path if ok else f"{path}\n（没有 configuration.xml，可能不是 RA 工程）")
        self._expand_src()
        return ok

    def clear_root(self):
        self._root = ""
        self._tree.setRootIndex(self._model.index(""))
        self._title.setText("📂 未打开工程")
        self._title.setToolTip("")

    def reveal(self, file_path: str):
        """在树里选中某个文件（比如 AI 改过它之后）。"""
        if not file_path or not self._root:
            return
        idx = self._model.index(file_path)
        if idx.isValid():
            self._tree.setCurrentIndex(idx)
            self._tree.scrollTo(idx)

    def refresh(self):
        """外部改动过文件后刷新（QFileSystemModel 自己会监听，这里是兜底）。"""
        if self._root:
            self._model.setRootPath("")
            self._model.setRootPath(self._root)
            self._tree.setRootIndex(self._model.index(self._root))
            self._expand_src()

    # ---- 内部 ----

    def _expand_src(self):
        src = os.path.join(self._root, "src")
        if os.path.isdir(src):
            idx = self._model.index(src)
            if idx.isValid():
                self._tree.expand(idx)

    def _on_activated(self, index):
        path = self._model.filePath(index)
        if path and os.path.isfile(path):
            self.file_activated.emit(path)

    # ---- 右键菜单 ----

    def _path_at(self, pos):
        """右键点到的路径；点在空白处就当作工程根。"""
        idx = self._tree.indexAt(pos)
        return self._model.filePath(idx) if idx.isValid() else self._root

    def _target_dir(self, path: str) -> str:
        """新建操作的落点：点在目录上就是它，点在文件上就是它所在目录。"""
        if not path:
            return self._root
        return path if os.path.isdir(path) else os.path.dirname(path)

    def _menu(self, pos):
        if not self._root:
            return
        path = self._path_at(pos)
        is_root = os.path.normpath(path) == os.path.normpath(self._root)

        menu = QMenu(self)
        act_file = QAction("📄 新建文件…", menu)
        act_file.triggered.connect(lambda: self._new_file(self._target_dir(path)))
        act_dir = QAction("📁 新建文件夹…", menu)
        act_dir.triggered.connect(lambda: self._new_dir(self._target_dir(path)))
        menu.addAction(act_file)
        menu.addAction(act_dir)

        if not is_root:
            menu.addSeparator()
            act_rename = QAction("✏️ 重命名…", menu)
            act_rename.triggered.connect(lambda: self._rename(path))
            act_del = QAction("🗑️ 删除", menu)
            act_del.triggered.connect(lambda: self._delete(path))
            menu.addAction(act_rename)
            menu.addAction(act_del)

        menu.addSeparator()
        act_term = QAction("💻 在此处打开终端", menu)
        act_term.triggered.connect(lambda: self._open_terminal(self._target_dir(path)))
        menu.addAction(act_term)

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _open_terminal(self, directory: str):
        """拉起系统终端，cwd 落在这个目录。

        不自己做终端控件：那要处理 PTY、ANSI 颜色码、交互式程序，
        而学生真需要命令行的时候，系统终端比我们能做出来的任何东西都好用。
        """
        if not os.path.isdir(directory):
            return
        launched = ""
        for program, args in _terminal_candidates():
            if not (os.path.isabs(program) or shutil.which(program)):
                continue
            if QProcess.startDetached(program, args, directory):
                launched = program
                break
        logger.info("在 {} 打开终端：{}", directory, launched or "全部失败")
        if not launched:
            QMessageBox.information(
                self, "打不开终端",
                "没找到可用的终端程序。\n可以设置环境变量 TERMINAL 指定一个。\n\n"
                f"目录是：\n{directory}")

    def _ask_name(self, title: str, default: str = "") -> str:
        name, ok = QInputDialog.getText(self, title, "名称：", text=default)
        return name.strip() if ok else ""

    def _new_file(self, folder: str):
        name = self._ask_name("新建文件")
        if not name:
            return
        target = os.path.join(folder, name)
        if os.path.exists(target):
            QMessageBox.warning(self, "已存在", f"{name} 已经存在了。")
            return
        try:
            # 新建 .h 顺手写好头文件保护，省得学生漏掉
            content = ""
            if name.lower().endswith((".h", ".hpp")):
                guard = "".join(c.upper() if c.isalnum() else "_" for c in name)
                content = f"#ifndef {guard}\n#define {guard}\n\n\n\n#endif /* {guard} */\n"
            with open(target, "w", encoding="utf-8", newline="") as f:
                f.write(content)
        except OSError as e:
            QMessageBox.warning(self, "新建失败", str(e))
            return
        self.file_created.emit(target)

    def _new_dir(self, folder: str):
        name = self._ask_name("新建文件夹")
        if not name:
            return
        try:
            os.makedirs(os.path.join(folder, name), exist_ok=False)
        except OSError as e:
            QMessageBox.warning(self, "新建失败", str(e))

    def _rename(self, path: str):
        old = os.path.basename(path)
        name = self._ask_name("重命名", old)
        if not name or name == old:
            return
        target = os.path.join(os.path.dirname(path), name)
        if os.path.exists(target):
            QMessageBox.warning(self, "已存在", f"{name} 已经存在了。")
            return
        try:
            os.rename(path, target)
        except OSError as e:
            QMessageBox.warning(self, "重命名失败", str(e))

    def _delete(self, path: str):
        name = os.path.basename(path)
        kind = "文件夹" if os.path.isdir(path) else "文件"
        if QMessageBox.question(
                self, "确认删除", f"确定删除{kind} {name} 吗？此操作不可撤销。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as e:
            QMessageBox.warning(self, "删除失败", str(e))
