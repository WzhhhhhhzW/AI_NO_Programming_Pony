LIGHT_STYLESHEET = """
QMainWindow {
    background-color: #f5f5f7;
}
QWidget {
    color: #1d1d1f;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
}
QFrame#top_bar {
    background-color: #ffffff;
    border-bottom: 1px solid #d2d2d7;
}
QLabel {
    font-weight: bold;
    color: #1d1d1f;
}
QLabel#title_label {
    font-size: 14px;
    font-weight: bold;
    color: #0078d4;
}
QPushButton {
    background-color: #f5f5f7;
    color: #1d1d1f;
    border: 1px solid #d2d2d7;
    border-radius: 4px;
    padding: 4px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #e8e8ed;
    border-color: #8e8e93;
}
QPushButton:disabled {
    background-color: #f5f5f7;
    color: #aeaeaf;
    border-color: #e5e5ea;
}
QPushButton#btn_send {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
}
QPushButton#btn_send:hover {
    background-color: #005a9e;
}
QPushButton#btn_explain {
    background-color: #e1f5fe;
    border-color: #b3e5fc;
    color: #0288d1;
}
QPushButton#btn_explain:hover {
    background-color: #b3e5fc;
}
QTextEdit#code_edit {
    background-color: #ffffff;
    color: #24292e;
    border: 1px solid #d2d2d7;
    border-radius: 4px;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 14px;
    padding: 8px;
}
QWidget#chat_log {
    background-color: #f9f9fb;
    border: 1px solid #d2d2d7;
    border-radius: 4px;
    padding: 8px;
}
QLineEdit#txt_input {
    background-color: #ffffff;
    color: #1d1d1f;
    border: 1px solid #d2d2d7;
    border-radius: 4px;
    padding: 6px;
}
QLineEdit#txt_input:focus {
    border: 1px solid #0078d4;
}
QComboBox {
    background-color: #ffffff;
    color: #1d1d1f;
    border: 1px solid #d2d2d7;
    border-radius: 4px;
    padding: 2px 8px;
    min-width: 150px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1d1d1f;
    selection-background-color: #0078d4;
    selection-color: #ffffff;
}
QSplitter::handle {
    background-color: #e5e5ea;
}
QStatusBar {
    background-color: #ffffff;
    color: #8e8e93;
    border-top: 1px solid #d2d2d7;
}
QFrame#toolbar_sep { background-color: #d8d8dd; border: none; margin: 6px 2px; }
QLabel#lbl_lesson {
    color: #6b6f76; font-size: 12px; padding: 0 8px;
    min-width: 150px;
}
QPushButton#btn_lesson_nav {
    background-color: #f2f2f5; color: #1d1d1f;
    border: 1px solid #d8d8dd; border-radius: 4px; padding: 3px 10px;
}
QPushButton#btn_lesson_nav:hover { background-color: #e6e6ea; }
QPushButton#btn_lesson_nav:disabled { color: #b0b3b8; background-color: #f7f7f9; }
QProgressBar#lesson_progress {
    background-color: #e6e6ea; border: none; border-radius: 2px;
}
QProgressBar#lesson_progress::chunk { background-color: #007AFF; border-radius: 2px; }
QLabel#tree_title { color: #6b6f76; font-size: 12px; font-weight: bold; padding: 2px 0; }
QTreeView#project_tree {
    background-color: #ffffff; color: #1d1d1f;
    border: 1px solid #e0e0e5; border-radius: 6px;
    font-size: 12px; outline: none;
}
QTreeView#project_tree::item { padding: 3px 2px; }
QTreeView#project_tree::item:hover { background-color: #f0f0f4; }
QTreeView#project_tree::item:selected { background-color: #007aff; color: #ffffff; }
QMessageBox { background-color: #ffffff; }
QMessageBox QLabel { color: #1d1d1f; font-size: 13px; }
QMessageBox QPushButton {
    background-color: #f2f2f5; color: #1d1d1f;
    border: 1px solid #d2d2d7; border-radius: 4px;
    padding: 6px 18px; min-width: 72px; font-weight: bold;
}
QMessageBox QPushButton:hover { background-color: #e6e6ea; border-color: #b8b8bf; }
QMessageBox QPushButton:default { background-color: #0078d4; color: #ffffff; border: none; }
QMessageBox QPushButton:default:hover { background-color: #1c97f3; }
QFileDialog { background-color: #ffffff; color: #1d1d1f; }
QMenu { background-color: #ffffff; color: #1d1d1f; border: 1px solid #d8d8dd; padding: 4px; }
QMenu::item { padding: 6px 22px 6px 14px; border-radius: 4px; }
QMenu::item:selected { background-color: #007aff; color: #ffffff; }
QMenu::separator { height: 1px; background: #e0e0e5; margin: 4px 8px; }
QInputDialog { background-color: #ffffff; }
QInputDialog QLabel { color: #1d1d1f; }
QInputDialog QLineEdit {
    background-color: #ffffff; color: #1d1d1f;
    border: 1px solid #d2d2d7; border-radius: 4px; padding: 6px;
}
QInputDialog QPushButton {
    background-color: #f2f2f5; color: #1d1d1f; border: 1px solid #d2d2d7;
    border-radius: 4px; padding: 6px 18px; min-width: 72px;
}
QInputDialog QPushButton:hover { background-color: #e6e6ea; }
QLabel#editor_empty { color: #8a8a8f; font-size: 13px; background-color: #ffffff; }
QTabWidget#editor_tabs::pane { border: 1px solid #e0e0e5; border-radius: 4px; top: -1px; }
QTabBar::tab {
    background-color: #f2f2f5; color: #6b6f76;
    border: 1px solid #e0e0e5; border-bottom: none;
    border-top-left-radius: 5px; border-top-right-radius: 5px;
    padding: 5px 12px; margin-right: 2px; font-size: 12px;
}
QTabBar::tab:selected { background-color: #ffffff; color: #1d1d1f; }
QTabBar::tab:hover:!selected { background-color: #e8e8ec; }
QTabBar::close-button { subcontrol-position: right; }
QPushButton#tab_close {
    background: transparent; color: #9aa0a6; border: none;
    border-radius: 8px; font-size: 11px; padding: 0;
}
QPushButton#tab_close:hover { background-color: #e05c50; color: #ffffff; }
QScrollBar:vertical {
    background: #f2f2f5; width: 11px; margin: 0; border: none;
}
QScrollBar:horizontal {
    background: #f2f2f5; height: 11px; margin: 0; border: none;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #c6c6cc; border-radius: 5px; min-height: 28px; min-width: 28px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #a8a8b0;
}
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; border: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
/* 两条滚动条交汇处那一小块。属于滚动区域而不是滚动条，
   写成 QScrollBar::corner 是无效选择器，编辑器右下角那个黑方块就是这么来的 */
QAbstractScrollArea::corner { background: #f2f2f5; border: none; }
/* 标签放不下时右侧会出现的左右翻页按钮，不写样式就是系统那两个黑方块 */
QTabBar QToolButton {
    background-color: #f2f2f5; color: #4a4a50;
    border: 1px solid #d8d8dd; border-radius: 4px; margin: 2px;
}
QTabBar QToolButton:hover { background-color: #e2e2e8; }
QTabBar::scroller { width: 34px; }
/* ---- 编辑器下面的输出面板 ---- */
QWidget#output_panel { background-color: #ffffff; }
QTabWidget#output_tabs::pane {
    border: none; border-top: 1px solid #e0e0e6; background-color: #ffffff;
}
QTabWidget#output_tabs QTabBar::tab {
    background: transparent; color: #6a6a70; border: none;
    padding: 5px 14px; font-size: 12px;
}
QTabWidget#output_tabs QTabBar::tab:selected {
    color: #1d1d1f; font-weight: 600; border-bottom: 2px solid #007aff;
}
QTabWidget#output_tabs QTabBar::tab:hover { color: #1d1d1f; }
QPlainTextEdit#output_log {
    background-color: #fbfbfd; color: #24292e; border: none; padding: 6px 8px;
}
QTreeWidget#problem_list {
    background-color: #fbfbfd; color: #24292e; border: none;
    alternate-background-color: #f4f4f7;
}
QTreeWidget#problem_list::item { padding: 3px 4px; }
QTreeWidget#problem_list::item:selected { background-color: #d8e8ff; color: #1d1d1f; }
QTreeWidget#problem_list QHeaderView::section {
    background-color: #f0f0f4; color: #6a6a70; border: none;
    border-right: 1px solid #e0e0e6; padding: 4px 8px; font-size: 11px;
}
QPushButton#output_close {
    background: transparent; color: #9aa0a6; border: none;
    border-radius: 4px; font-size: 12px; padding: 0;
}
QPushButton#output_close:hover { background-color: #e2e2e8; color: #1d1d1f; }
"""

MODERN_STYLESHEET = """
QMainWindow {
    background-color: #121214;
}
QWidget {
    color: #c5c5c9;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
}
QFrame#top_bar {
    background-color: #1a1a1e;
    border-bottom: 1px solid #2d2d30;
}
QLabel {
    font-weight: bold;
    color: #e3e3e7;
}
QLabel#title_label {
    font-size: 14px;
    font-weight: bold;
    color: #007acc;
}
QPushButton {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 4px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2d2d30;
    color: #ffffff;
    border-color: #555555;
}
QPushButton:disabled {
    background-color: #18181c;
    color: #555555;
    border-color: #252526;
}
QPushButton#btn_send {
    background-color: #007acc;
    color: #ffffff;
    border: none;
}
QPushButton#btn_send:hover {
    background-color: #1c97f3;
}
QPushButton#btn_explain {
    background-color: #2b5b84;
    border-color: #3b6b94;
    color: #ffffff;
}
QPushButton#btn_explain:hover {
    background-color: #3b6b94;
}
QTextEdit#code_edit {
    background-color: #1e1e1e;
    color: #9cdcfe;
    border: 1px solid #2d2d30;
    border-radius: 4px;
    font-family: 'Consolas', 'Fira Code', monospace;
    font-size: 14px;
    padding: 8px;
}
QWidget#chat_log {
    background-color: #18181c;
    border: 1px solid #2d2d30;
    border-radius: 4px;
    padding: 8px;
}
QLineEdit#txt_input {
    background-color: #252526;
    color: #ffffff;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 6px;
}
QLineEdit#txt_input:focus {
    border: 1px solid #007acc;
}
QComboBox {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 2px 8px;
    min-width: 150px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #cccccc;
    selection-background-color: #007acc;
    selection-color: #ffffff;
}
QSplitter::handle {
    background-color: #252526;
}
QStatusBar {
    background-color: #1a1a1e;
    color: #888888;
    border-top: 1px solid #2d2d30;
}
QFrame#toolbar_sep { background-color: #3a3a3f; border: none; margin: 6px 2px; }
QLabel#lbl_lesson {
    color: #9aa0a6; font-size: 12px; padding: 0 8px;
    min-width: 150px;
}
QPushButton#btn_lesson_nav {
    background-color: #2a2d34; color: #d8dade;
    border: 1px solid #3a3d44; border-radius: 4px; padding: 3px 10px;
}
QPushButton#btn_lesson_nav:hover { background-color: #343841; }
QPushButton#btn_lesson_nav:disabled { color: #5a5d63; background-color: #232529; }
QProgressBar#lesson_progress {
    background-color: #2a2d34; border: none; border-radius: 2px;
}
QProgressBar#lesson_progress::chunk { background-color: #0A84FF; border-radius: 2px; }
QLabel#tree_title { color: #9aa0a6; font-size: 12px; font-weight: bold; padding: 2px 0; }
QTreeView#project_tree {
    background-color: #17171a; color: #c5c5c9;
    border: 1px solid #2a2a30; border-radius: 6px;
    font-size: 12px; outline: none;
}
QTreeView#project_tree::item { padding: 3px 2px; }
QTreeView#project_tree::item:hover { background-color: #232329; }
QTreeView#project_tree::item:selected { background-color: #0a84ff; color: #ffffff; }
QMessageBox { background-color: #1e1e1e; }
QMessageBox QLabel { color: #e3e3e7; font-size: 13px; }
QMessageBox QPushButton {
    background-color: #252526; color: #cccccc;
    border: 1px solid #3e3e42; border-radius: 4px;
    padding: 6px 18px; min-width: 72px; font-weight: bold;
}
QMessageBox QPushButton:hover { background-color: #2d2d30; border-color: #555555; }
QMessageBox QPushButton:default { background-color: #007acc; color: #ffffff; border: none; }
QMessageBox QPushButton:default:hover { background-color: #1c97f3; }
QFileDialog { background-color: #1e1e1e; color: #e3e3e7; }
QMenu { background-color: #1e1e1e; color: #e3e3e7; border: 1px solid #3a3a3f; padding: 4px; }
QMenu::item { padding: 6px 22px 6px 14px; border-radius: 4px; }
QMenu::item:selected { background-color: #0a84ff; color: #ffffff; }
QMenu::separator { height: 1px; background: #3a3a3f; margin: 4px 8px; }
QInputDialog { background-color: #1e1e1e; }
QInputDialog QLabel { color: #e3e3e7; }
QInputDialog QLineEdit {
    background-color: #252526; color: #ffffff;
    border: 1px solid #3e3e42; border-radius: 4px; padding: 6px;
}
QInputDialog QPushButton {
    background-color: #252526; color: #cccccc; border: 1px solid #3e3e42;
    border-radius: 4px; padding: 6px 18px; min-width: 72px;
}
QInputDialog QPushButton:hover { background-color: #2d2d30; }
QLabel#editor_empty { color: #6a6a70; font-size: 13px; background-color: #1e1e1e; }
QTabWidget#editor_tabs::pane { border: 1px solid #2a2a30; border-radius: 4px; top: -1px; }
QTabBar::tab {
    background-color: #202024; color: #9aa0a6;
    border: 1px solid #2a2a30; border-bottom: none;
    border-top-left-radius: 5px; border-top-right-radius: 5px;
    padding: 5px 12px; margin-right: 2px; font-size: 12px;
}
QTabBar::tab:selected { background-color: #1e1e1e; color: #e5e5ea; }
QTabBar::tab:hover:!selected { background-color: #26262b; }
QTabBar::close-button { subcontrol-position: right; }
QPushButton#tab_close {
    background: transparent; color: #7a7a80; border: none;
    border-radius: 8px; font-size: 11px; padding: 0;
}
QPushButton#tab_close:hover { background-color: #c0392b; color: #ffffff; }
QScrollBar:vertical {
    background: #1a1a1e; width: 11px; margin: 0; border: none;
}
QScrollBar:horizontal {
    background: #1a1a1e; height: 11px; margin: 0; border: none;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: #3a3a42; border-radius: 5px; min-height: 28px; min-width: 28px;
}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
    background: #4d4d57;
}
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; border: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
/* 见亮色那份的注释：这里必须是 QAbstractScrollArea::corner */
QAbstractScrollArea::corner { background: #1a1a1e; border: none; }
/* 标签放不下时右侧会出现的左右翻页按钮，不写样式就是系统那两个黑方块 */
QTabBar QToolButton {
    background-color: #26262b; color: #c5c5c9;
    border: 1px solid #3a3a42; border-radius: 4px; margin: 2px;
}
QTabBar QToolButton:hover { background-color: #33333a; }
QTabBar::scroller { width: 34px; }
/* ---- 编辑器下面的输出面板 ---- */
QWidget#output_panel { background-color: #16161a; }
QTabWidget#output_tabs::pane {
    border: none; border-top: 1px solid #2c2c32; background-color: #16161a;
}
QTabWidget#output_tabs QTabBar::tab {
    background: transparent; color: #8e8e93; border: none;
    padding: 5px 14px; font-size: 12px;
}
QTabWidget#output_tabs QTabBar::tab:selected {
    color: #e5e5ea; font-weight: 600; border-bottom: 2px solid #0a84ff;
}
QTabWidget#output_tabs QTabBar::tab:hover { color: #e5e5ea; }
QPlainTextEdit#output_log {
    background-color: #121215; color: #d4d4d4; border: none; padding: 6px 8px;
}
QTreeWidget#problem_list {
    background-color: #121215; color: #d4d4d4; border: none;
    alternate-background-color: #17171b;
}
QTreeWidget#problem_list::item { padding: 3px 4px; }
QTreeWidget#problem_list::item:selected { background-color: #24384f; color: #ffffff; }
QTreeWidget#problem_list QHeaderView::section {
    background-color: #1c1c20; color: #8e8e93; border: none;
    border-right: 1px solid #2c2c32; padding: 4px 8px; font-size: 11px;
}
QPushButton#output_close {
    background: transparent; color: #7a7a80; border: none;
    border-radius: 4px; font-size: 12px; padding: 0;
}
QPushButton#output_close:hover { background-color: #33333a; color: #e5e5ea; }
"""


# --------------- 对话框统一样式 ---------------
# 原来 5 个对话框各自硬编码一份暗色 QSS，亮色模式下就露馅了。
# 统一成一份，按主题取色；accent_button 是主操作按钮的 objectName。

_DIALOG_PALETTE = {
    "dark": dict(
        bg="#1e1e1e", fg="#e3e3e7", sub="#8E8E93",
        field_bg="#252526", field_fg="#ffffff", border="#3e3e42",
        btn_bg="#252526", btn_fg="#cccccc", btn_hover="#2d2d30", btn_hover_border="#555555",
        accent="#007acc", accent_hover="#1c97f3",
    ),
    "light": dict(
        bg="#ffffff", fg="#1d1d1f", sub="#6b6f76",
        field_bg="#ffffff", field_fg="#1d1d1f", border="#d2d2d7",
        btn_bg="#f2f2f5", btn_fg="#1d1d1f", btn_hover="#e6e6ea", btn_hover_border="#b8b8bf",
        accent="#0078d4", accent_hover="#1c97f3",
    ),
}


def dialog_stylesheet(theme: str = "dark", accent_button: str = "", accent_all: bool = False) -> str:
    """返回对话框 QSS。accent_all=True 时所有按钮都用强调色（知识详解那种）。"""
    p = _DIALOG_PALETTE.get(theme, _DIALOG_PALETTE["dark"])
    btn = (f"background-color: {p['accent']}; color: #ffffff; border: none;"
           if accent_all else
           f"background-color: {p['btn_bg']}; color: {p['btn_fg']}; border: 1px solid {p['border']};")
    btn_hover = (f"background-color: {p['accent_hover']};"
                 if accent_all else
                 f"background-color: {p['btn_hover']}; border-color: {p['btn_hover_border']};")
    qss = f"""
QDialog {{ background-color: {p['bg']}; }}
QLabel {{ color: {p['fg']}; font-size: 13px;
          font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; }}
QLineEdit, QTextEdit, QTextBrowser, QPlainTextEdit {{
    background-color: {p['field_bg']}; color: {p['field_fg']};
    border: 1px solid {p['border']}; border-radius: 4px;
    padding: 6px; font-size: 13px;
}}
QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {p['accent']}; }}
QComboBox {{
    background-color: {p['field_bg']}; color: {p['field_fg']};
    border: 1px solid {p['border']}; border-radius: 4px; padding: 5px 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {p['field_bg']}; color: {p['field_fg']};
    selection-background-color: {p['accent']}; selection-color: #ffffff;
}}
QCheckBox {{ color: {p['fg']}; spacing: 6px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 3px;
    border: 1px solid {p['border']}; background-color: {p['field_bg']};
}}
QCheckBox::indicator:hover {{ border-color: {p['accent']}; }}
QCheckBox::indicator:checked {{
    background-color: {p['accent']}; border-color: {p['accent']};
}}
QPushButton {{
    {btn}
    border-radius: 4px; padding: 6px 18px; font-weight: bold;
}}
QPushButton:hover {{ {btn_hover} }}
QPushButton:disabled {{ color: {p['sub']}; }}
"""
    if accent_button:
        qss += (f"QPushButton#{accent_button} {{ background-color: {p['accent']};"
                f" color: #ffffff; border: none; }}\n"
                f"QPushButton#{accent_button}:hover {{ background-color: {p['accent_hover']}; }}\n")
    return qss


def dialog_panel_style(theme: str = "dark") -> str:
    """对话框里"说明文字块"的样式（灰底方框）。"""
    p = _DIALOG_PALETTE.get(theme, _DIALOG_PALETTE["dark"])
    panel = "#18181c" if theme == "dark" else "#f5f5f7"
    return (f"color: {p['sub']}; font-size: 12px; background-color: {panel}; "
            f"border: 1px solid {p['border']}; border-radius: 4px; padding: 8px;")


def dialog_readonly_text_style(theme: str = "dark") -> str:
    """知识详解那种只读大文本区。"""
    p = _DIALOG_PALETTE.get(theme, _DIALOG_PALETTE["dark"])
    panel = "#18181c" if theme == "dark" else "#f7f7f9"
    return f"""
QTextEdit {{
    background-color: {panel}; color: {p['fg']};
    border: 1px solid {p['border']}; border-radius: 4px;
    padding: 12px; font-size: 14px;
}}
"""


def dialog_accent_title_color(theme: str = "dark") -> str:
    return "#4EC9B0" if theme == "dark" else "#0a7d68"

