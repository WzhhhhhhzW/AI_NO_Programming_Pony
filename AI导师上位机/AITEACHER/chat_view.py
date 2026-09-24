"""对话区。

底层是一个 QWebEngineView，内容就是一张普通网页（见 chat_page.py）。

换掉 Qt 富文本的原因：它只认 HTML4 子集——块级元素的背景不渲染、围栏
代码块被拆成一行一个 <pre>、一半 CSS 属性无效，只能靠正则打补丁。那条
路越走越脏，而且组里没人愿意去记 Qt 到底支持哪几条 CSS。改成网页之后，
调样式就是改 CSS，还顺带拿到了语法高亮和平滑滚动。

对外接口和之前的控件版一致，所以 ui_main 不用改：

    view.add_user(text)
    view.add_system(html)
    view.add_lesson(header, markdown)
    bubble = view.begin_assistant()
    bubble.append_text(chunk) / add_tool(...) / add_denied(...) / finish(cost)
"""

import json

from PyQt6.QtCore import QTimer, QUrl, QUrlQuery, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from loguru import logger

import chat_page
import markdown_render

_THEMES = ("dark", "light")


class _Page(QWebEnginePage):
    """拦下页面里 ``horse:`` 开头的链接，转成 Qt 信号。

    页面里的按钮全是 ``<a href="horse:build">`` 这种。用自定义协议而不是
    QtWebChannel：少一个模块依赖、不用往页面里注入 qwebchannel.js，
    而且点击本来就会走 acceptNavigationRequest，拦得干净。
    """

    action = pyqtSignal(str, dict)

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame):
        if url.scheme() == "horse":
            # horse:send?text=xxx  →  path="send", query="text=xxx"
            name = url.path() or url.host()
            query = QUrlQuery(url.query())
            params = {k: v for k, v in query.queryItems(
                QUrl.ComponentFormattingOption.FullyDecoded)}
            logger.info("对话区按钮：{} {}", name, params)
            self.action.emit(name, params)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


def _js(value) -> str:
    """把 Python 值安全地塞进 JS 调用（引号、换行、中文都不用操心）。"""
    return json.dumps(value, ensure_ascii=False)


class AssistantBubble:
    """一条正在生长的 AI 回复。

    内容是一条**时间线**：``[("text", 原文), ("tool", 图标, 名字, 参数, 是否被拒), ...]``，
    按到达顺序排。模型一轮里天然是"说半句→调工具→再说半句"，把所有文字拼成
    一个字符串渲染的话，那些半句会糊成一大坨读不了。

    流式期间每 70ms 把**当前这一段**重排一次 Markdown。消息只有几 KB，重排代价
    可以忽略，好处是代码块和表格在收完之前就已经是排好版的。
    """

    def __init__(self, view: "ChatView", node_id: str):
        self._view = view
        self._id = node_id
        self._blocks: list[tuple] = []   # 已经定稿的块
        self._cur = ""                   # 正在流入的这一段文字
        self._done = False
        self._dirty = False
        self._timer = QTimer(view)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._flush)
        self._timer.start()

    # ---- 内容 ----

    def append_text(self, chunk: str):
        if not chunk or self._done:
            return
        self._cur += chunk
        self._dirty = True

    def add_tool(self, name: str, detail: str, icon: str = "🔍"):
        self._push_tool(icon, name, detail, False)

    def add_denied(self, name: str, reason: str):
        self._push_tool("🚫", name, reason, True)

    def set_status(self, text: str):
        """保留接口。页面上用闪烁光标表示"进行中"，不需要额外文字。"""

    def finish(self, cost: str = ""):
        self._close_text()
        self._done = True
        self._timer.stop()
        self._view._call("botFinish", self._id, cost)

    @property
    def raw_text(self) -> str:
        """整轮的纯文字（给"知识详解"和主题重放用），工具行不算。"""
        parts = [b[1] for b in self._blocks if b[0] == "text"]
        if self._cur:
            parts.append(self._cur)
        return "\n\n".join(parts)

    def replay(self):
        """换主题重建页面后，按原顺序重新铺一遍。"""
        for i, block in enumerate(self._blocks):
            if block[0] == "text":
                self._view._call("botText", self._id, i,
                                 markdown_render.render(block[1]))
            else:
                self._view._call("botTool", self._id, *block[1:])
        if self._cur:
            self._flush(force=True)
        if self._done:
            self._view._call("botFinish", self._id, "")

    # ---- 内部 ----

    def _push_tool(self, icon, name, detail, deny):
        # 工具调用一来就说明上一段文字讲完了，先给它定稿再排工具行
        self._close_text()
        self._blocks.append(("tool", icon, name, detail, deny))
        self._view._call("botTool", self._id, icon, name, detail, deny)

    def _close_text(self):
        if self._cur.strip():
            self._flush(force=True)
            self._blocks.append(("text", self._cur))
        self._cur = ""
        self._dirty = False

    def _flush(self, force: bool = False):
        if not (self._dirty or force) or not self._cur.strip():
            return
        self._dirty = False
        # 在流的段号 = 已定稿块的个数，所以同一段的多次刷新会落在同一个 div 上
        self._view._call("botText", self._id, len(self._blocks),
                         markdown_render.render(self._cur))


class ChatView(QWidget):
    """消息列表。UI 只跟它打交道，不碰 HTML 也不碰 JS。"""

    ready = pyqtSignal()
    action = pyqtSignal(str, dict)      # 页面上的按钮被点了

    def __init__(self, theme: str = "dark", parent=None):
        super().__init__(parent)
        self._theme = theme if theme in _THEMES else "dark"
        self._seq = 0
        self._history: list[tuple] = []   # 换主题时重放用
        self._bubbles: dict[str, AssistantBubble] = {}
        self._queue: list[str] = []       # 页面加载完成前先攒着
        self._loaded = False

        # 不设成 Expanding 的话，外层 QVBoxLayout 会把多余的竖直空间平摊给
        # 每一项，"AI 导师"那行标题就会被推到中间去
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._web = QWebEngineView(self)
        self._web.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._page = _Page(self._web)
        self._page.action.connect(self.action)
        self._web.setPage(self._page)
        lay.addWidget(self._web)
        self._web.loadFinished.connect(self._on_loaded)
        self._reload_page()

    # ---- 页面 ----

    _BG = {"dark": "#121214", "light": "#f5f5f7"}

    def _reload_page(self):
        self._loaded = False
        # 页面要整个重建，之前攒下还没执行的调用作废——换主题时调用方会
        # 用 _history 重放一遍，不清空就会重复插入（开场卡片出现两张）
        self._queue.clear()
        # 先把 web 页的底色设成目标主题色，否则 setHtml 期间会闪一下默认白底，
        # 表现为"对话区下面那块矩形比别处慢半拍才变色"
        self._web.page().setBackgroundColor(QColor(self._BG[self._theme]))
        self._web.setHtml(chat_page.page_html(
            self._theme, markdown_render.pygments_css(self._theme)))

    def _on_loaded(self, ok: bool):
        """页面加载结束。

        **只认 ok=True。** 因为点页面里的 ``horse:`` 按钮时，
        ``acceptNavigationRequest`` 返回 False 拦掉跳转，Qt 会把这次被拦下的
        导航当成"加载失败"，照样发一个 ``loadFinished(False)``。以前在这里
        无脑 ``self._loaded = ok``，于是**学生点一次按钮，页面就被标记成没加载
        完，之后所有 addUser / botBody / addDiff 全部进队列不再执行**——界面
        表现就是 AI 永远在转圈、一个字都不出，但文件其实已经改好了。
        """
        if not ok:
            logger.debug("有一次导航被拦下（点了页面里的按钮），不动加载状态")
            return
        self._loaded = True
        logger.info("对话区页面加载完成，补发 {} 条排队调用", len(self._queue))
        for js in self._queue:
            self._web.page().runJavaScript(js, self._js_result)
        self._queue.clear()
        self.ready.emit()

    def _call(self, fn: str, *args):
        # 包一层 try/catch：runJavaScript 里抛异常是**静音**的，页面上就是
        # "这条消息没出现"，什么线索都没有。抓回来打日志。
        inner = f"{fn}({','.join(_js(a) for a in args)});"
        js = f"try{{{inner}}}catch(e){{'JS_ERROR '+fn+': '+e.message}}"
        js = js.replace("+fn+", "+" + _js(fn) + "+")
        if self._loaded:
            self._web.page().runJavaScript(js, self._js_result)
        else:
            self._queue.append(js)

    @staticmethod
    def _js_result(value):
        if isinstance(value, str) and value.startswith("JS_ERROR"):
            logger.error("对话区网页报错：{}", value)

    # ---- 添加消息 ----

    def add_user(self, text: str):
        self._history.append(("user", text))
        self._call("addUser", text)

    def add_system(self, text: str):
        # 允许少量 HTML：调用方用它做加粗和换行
        html_text = text.replace("\n", "<br>")
        self._history.append(("sys", html_text))
        self._call("addSystem", html_text)

    def add_lesson(self, header: str, body: str):
        self._history.append(("lesson", header, body))
        self._call("addLesson", header, markdown_render.render(body))

    def add_quick(self, title: str, subtitle: str, items: list):
        """开场的快捷指令卡片。items 是 [{icon, label, text}, ...]。"""
        self._history.append(("quick", title, subtitle, items))
        self._call("addQuick", title, subtitle, items)

    def add_diff(self, diff: dict):
        """一个文件的改动。字段见 chat_page.js 的 addDiff。"""
        self._history.append(("diff", diff))
        self._call("addDiff", diff)

    def add_actions(self, node_id: str, text: str, hint: str = "") -> str:
        """改完之后那条【编译】/【撤销】动作条。"""
        self._history.append(("act", node_id, text, hint))
        self._call("addActions", node_id, text, hint)
        return node_id

    def retire_actions(self, node_id: str, text: str = ""):
        """按钮点过之后收起来，防止重复撤销。"""
        for i, item in enumerate(self._history):
            if item[0] == "act" and item[1] == node_id:
                self._history[i] = ("act_done", node_id, text or item[2])
                break
        self._call("retireActions", node_id, text)

    def begin_assistant(self) -> AssistantBubble:
        self._seq += 1
        node_id = f"b{self._seq}"
        self._history.append(("bot", node_id))
        self._call("beginBot", node_id, "🤖 AI 导师")
        bubble = AssistantBubble(self, node_id)
        self._bubbles[node_id] = bubble
        return bubble

    def clear(self):
        for b in self._bubbles.values():
            b._timer.stop()
        self._bubbles.clear()
        self._history.clear()
        self._call("clearAll")

    # ---- 杂项 ----

    def scroll_to_bottom(self):
        self._call("toBottom", True)

    def set_theme(self, theme: str):
        """换主题。语法高亮的 class 定义在 <style> 里，只能整页重建后重放。"""
        theme = theme if theme in _THEMES else "dark"
        if theme == self._theme:
            return
        self._theme = theme
        self._reload_page()
        for item in self._history:
            kind = item[0]
            if kind == "user":
                self._call("addUser", item[1])
            elif kind == "sys":
                self._call("addSystem", item[1])
            elif kind == "lesson":
                self._call("addLesson", item[1], markdown_render.render(item[2]))
            elif kind == "quick":
                self._call("addQuick", item[1], item[2], item[3])
            elif kind == "diff":
                self._call("addDiff", item[1])
            elif kind == "act":
                self._call("addActions", item[1], item[2], item[3])
            elif kind == "act_done":
                self._call("addActions", item[1], item[2], "")
                self._call("retireActions", item[1], "")
            elif kind == "bot":
                node_id = item[1]
                bubble = self._bubbles.get(node_id)
                self._call("beginBot", node_id, "🤖 AI 导师")
                if bubble:
                    bubble.replay()
