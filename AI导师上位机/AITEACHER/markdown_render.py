"""Markdown → HTML，带代码语法高亮。

用 markdown-it-py 而不是 Qt 自带的解析器：Qt 那份产出的 HTML 带着一堆
写死的内联样式（等宽字体固定 9pt、每个块自带 margin），还会把围栏代码块
拆成一行一个 <pre>，想改样式只能上正则补丁。

Pygments 输出 CSS class（不是内联样式），明暗两套主题各生成一份 class 定义，
换主题时整体换掉即可。
"""

import html as _html

from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

# 嵌入式教学场景基本只会出现这几种
_LANG_ALIAS = {"c": "c", "h": "c", "cpp": "cpp", "c++": "cpp",
               "py": "python", "sh": "bash", "shell": "bash",
               "xml": "xml", "json": "json", "make": "make", "makefile": "make"}

_PYG_PREFIX = "hl"
_FORMATTER = HtmlFormatter(nowrap=True, classprefix=_PYG_PREFIX + "-")


def _highlight(code: str, lang: str) -> str:
    lang = _LANG_ALIAS.get((lang or "").strip().lower(), (lang or "").strip().lower())
    if not lang:
        return _html.escape(code)
    try:
        lexer = get_lexer_by_name(lang, stripall=False)
    except ClassNotFound:
        return _html.escape(code)
    return highlight(code, lexer, _FORMATTER)


def _fence(self, tokens, idx, options, env):      # markdown-it 的 fence 渲染器
    tok = tokens[idx]
    body = _highlight(tok.content.rstrip("\n"), tok.info)
    return f"<pre><code>{body}</code></pre>\n"


_MD = MarkdownIt("commonmark", {"html": False, "linkify": True, "breaks": False})
_MD.enable(["table", "strikethrough"])
_MD.add_render_rule("fence", _fence)


def render(text: str) -> str:
    """Markdown 片段 → HTML。html=False，所以模型输出里的标签不会被执行。"""
    return _MD.render(text or "")


def pygments_css(theme: str) -> str:
    """当前主题下的语法高亮配色。"""
    style = "monokai" if theme == "dark" else "friendly"
    css = HtmlFormatter(style=style, classprefix=_PYG_PREFIX + "-").get_style_defs("")
    # get_style_defs 产出的选择器形如 `.hl-k { ... }`，直接可用；
    # 但它也会带一条设定背景的规则，交给我们自己的 CSS 管，去掉。
    return "\n".join(line for line in css.splitlines()
                     if not line.strip().startswith(("pre {", "td.linenos", "span.linenos",
                                                     ".highlight")))
