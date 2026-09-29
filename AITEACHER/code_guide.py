"""高级模式参考代码面板；内容仅在内存中保存。"""

import re

from PyQt6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)
from code_editor import CodeEditor


def code_blocks(markdown):
    """保留多个代码块，也支持流式响应中尚未闭合的围栏。"""
    blocks = []
    fence = None
    language = ""
    lines = []
    for line in markdown.splitlines(keepends=True):
        if fence is None:
            match = re.match(r"^\s{0,3}(`{3,}|~{3,})([^\r\n]*)[\r\n]*$", line)
            if match:
                fence = match[1]
                language = match[2].strip() or "code"
                lines = []
        elif re.match(r"^\s{0,3}" + re.escape(fence[0]) + r"{" + str(len(fence)) + r",}\s*$", line):
            blocks.append((language, "".join(lines)))
            fence = None
        else:
            lines.append(line)
    if fence is not None and lines:
        # 未结束的末行可能是正在传输的闭合围栏，不将其显示为代码。
        if lines[-1].strip() and set(lines[-1].strip()) == {fence[0]}:
            lines.pop()
        blocks.append((language, "".join(lines)))
    return blocks


class CodeGuide(QWidget):
    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self.blocks = []
        self.reference_files = []
        layout = QVBoxLayout(self)
        title = QLabel("📖 代码指引")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        hint = QLabel("以 Dog 实例工程为准。右侧提出需求，这里直接提供对应原始文件供你复制。")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.status = QLabel("等待提问，例如：给我 PWM 舵机驱动的参考代码")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        bar = QHBoxLayout()
        self.selector = QComboBox()
        self.selector.currentIndexChanged.connect(self._select)
        bar.addWidget(self.selector, 1)
        self.copy_button = QPushButton("复制当前代码")
        self.copy_button.clicked.connect(self.copy_current)
        self.copy_button.setEnabled(False)
        bar.addWidget(self.copy_button)
        layout.addLayout(bar)
        self.code = CodeEditor(theme=theme)
        self.code.setReadOnly(True)
        layout.addWidget(self.code, 1)

    def begin(self, question):
        self.reference_files = []
        self.blocks = []
        self.selector.clear()
        self.code.setText("")
        self.copy_button.setEnabled(False)
        self.status.setText("正在生成：" + question)

    def show_reference(self, files):
        self.reference_files = files
        self.blocks = [("c", text) for _, text in files]
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.addItems(["Dog/" + name for name, _ in files])
        self.selector.setCurrentIndex(0)
        self.selector.blockSignals(False)
        self._select(0)
        self.copy_button.setEnabled(bool(files))
        self.status.setText("已载入 Dog 实例原始代码，可直接复制。")

    def update_response(self, response, done=False, failed=False):
        if self.reference_files:
            if failed:
                self.status.setText("AI 讲解暂不可用；Dog 原始代码仍可选择和复制。")
            elif done:
                self.status.setText("来源：Dog 实例工程原始文件。请按实例的 FSP 配置使用，讲解见右侧。")
            return
        blocks = code_blocks(response)
        if blocks != self.blocks:
            selected = max(0, self.selector.currentIndex())
            self.blocks = blocks
            self.selector.blockSignals(True)
            self.selector.clear()
            self.selector.addItems([f"代码片段 {i + 1} · {lang}" for i, (lang, _) in enumerate(blocks)])
            self.selector.setCurrentIndex(min(selected, len(blocks) - 1))
            self.selector.blockSignals(False)
            self._select(self.selector.currentIndex())
        self.copy_button.setEnabled(done and not failed and bool(blocks))
        if failed:
            self.status.setText("生成失败，右侧可查看原因。请重试；当前片段可能不完整。")
        elif done:
            self.status.setText("参考代码已生成，请结合课程与硬件配置检查后使用。" if blocks
                                else "本次回复为文字讲解，请查看右侧；可继续要求提供具体代码。")

    def _select(self, index):
        text = self.blocks[index][1] if 0 <= index < len(self.blocks) else ""
        if self.code.text() != text:
            scroll = self.code.verticalScrollBar().value()
            self.code.setText(text)
            self.code.verticalScrollBar().setValue(scroll)

    def copy_current(self):
        if self.copy_button.isEnabled():
            QApplication.clipboard().setText(self.code.text())
            self.status.setText("当前代码已复制，可粘贴到你的工程文件中。")
