"""AI 答疑层。

用 Claude Agent SDK 的 ``ClaudeSDKClient`` 开一条**常驻会话**，学生每次提问
只往里递一句话——对话上下文由 CLI 子进程自己维护，Python 侧不拼历史。
（实测：第 2 轮只用代词提问，input_tokens=10 就能答对。）

线程模型：SDK 是 async 的，Qt 是信号槽的，所以起一个 QThread，里面跑自己的
asyncio 事件循环；UI 线程通过 ``ask()`` 把问题塞进 asyncio 队列，回来的内容
一律走 Qt 信号，保证只在主线程碰控件。

权限是两道闸：
  闸1 ``allowed_tools``  —— 这个工具存不存在（高级模式压根没有 Edit）
  闸2 ``PreToolUse`` hook —— 这一次调用准不准（初级模式限制只能改 src/*.c|h）
注意 ``can_use_tool`` 回调在这里没用：只要工具在 allowed_tools 里，SDK 会在
回调之前就自动放行（它自己会打 CanUseToolShadowedWarning 警告）。
"""

import asyncio
import os
import queue
import sys
import time
from dataclasses import dataclass, field

from PyQt6.QtCore import QThread, pyqtSignal
from loguru import logger

# 只读答疑：能看，不能动
READONLY_TOOLS = ["Read", "Glob", "Grep"]
# 改码：多一个 Edit。刻意不给 Write —— 它能整文件覆盖，而改参数用不到
EDIT_TOOLS = READONLY_TOOLS + ["Edit"]

# 显式禁用。不写这一条也拦得住（实测 Bash 会被拒、文件不会被创建），
# 但模型会反复尝试再被拒，白白多几个回合——一次答疑里见过 5 次无效
# Bash 调用。写进 disallowed_tools 之后它压根不会去试。
# Bash 不给的原因：编译要走上位机自己的 BuildWorker，才能做"固件必须是
# 本次产出"的判定并把日志流进 UI。
BLOCKED_TOOLS = ["Bash", "BashOutput", "KillShell", "Task",
                 "WebFetch", "WebSearch", "NotebookEdit", "TodoWrite"]

_TOOL_LABEL = {
    "Read": "读取文件",
    "Glob": "查找文件",
    "Grep": "搜索内容",
    "Edit": "修改文件",
    "Write": "写入文件",
    "mcp__horse__compile_project": "编译自检",
}

_TOOL_ICON = {
    "Edit": "✏️",
    "Write": "✏️",
    "mcp__horse__compile_project": "🔨",
}


def _tool_detail(name: str, args: dict) -> str:
    """把工具入参压成一行人话。"""
    args = args or {}
    if name == "Read":
        return os.path.basename(str(args.get("file_path", "")))
    if name == "Glob":
        return str(args.get("pattern", ""))
    if name == "Grep":
        return str(args.get("pattern", ""))
    if name in ("Edit", "Write"):
        return os.path.basename(str(args.get("file_path", "")))
    if name.startswith("mcp__"):
        return ""
    return ", ".join(f"{k}={v}" for k, v in list(args.items())[:2])[:60]


WRITABLE_EXT = (".c", ".h", ".cpp", ".hpp")


@dataclass
class AdvisorConfig:
    """开一条会话需要的全部参数。"""
    project_root: str
    system_prompt: str
    base_url: str
    api_key: str
    model: str = "claude-haiku-4-5"
    allowed_tools: list = field(default_factory=lambda: list(READONLY_TOOLS))
    blocked_tools: list = field(default_factory=lambda: list(BLOCKED_TOOLS))
    max_turns: int = 24
    max_budget_usd: float = 0.5
    # 允许改动的目录（绝对路径）。空 = 一个都不许改。
    # 初级模式只放 <工程>/src：ra/ ra_gen/ ra_cfg/ 是 RASC 生成的，
    # 模型动了工程就废了，现场没法救。
    write_roots: list = field(default_factory=list)
    # 进程内 MCP server，{名字: config}。见 build_tool.make_server()
    mcp_servers: dict = field(default_factory=dict)


def bundled_cli_path() -> str:
    """打包之后 claude CLI 的位置；没打包返回空串（让 SDK 自己找）。

    SDK 是靠 ``Path(__file__)/../../../_bundled/claude`` 定位它自带的 CLI 的。
    冻结之后 ``__file__`` 指向 PyInstaller 的解压目录，只要打包时把 _bundled
    原样放进 ``claude_agent_sdk/`` 下面，这条路径其实也成立——但那是隐式依赖
    别人的实现细节，所以这里显式算一遍传给 ``cli_path``，找不到再退回去。
    """
    if not getattr(sys, "frozen", False):
        return ""
    name = "claude.exe" if os.name == "nt" else "claude"
    base = getattr(sys, "_MEIPASS", "") or os.path.dirname(sys.executable)
    for candidate in (
        os.path.join(base, "claude_agent_sdk", "_bundled", name),
        os.path.join(base, "_bundled", name),
    ):
        if os.path.isfile(candidate):
            logger.info("用打包进来的 claude CLI：{}", candidate)
            return candidate
    logger.warning("打包环境里没找到自带的 claude CLI，交给 SDK 自己去 PATH 里找")
    return ""


def _under(path: str, roots: list) -> bool:
    """path 是不是落在 roots 里某个目录下（含目录本身）。"""
    try:
        real = os.path.realpath(path)
    except OSError:
        return False
    for root in roots:
        try:
            if os.path.commonpath([real, os.path.realpath(root)]) == os.path.realpath(root):
                return True
        except ValueError:      # Windows 上不同盘符
            continue
    return False


def write_guard(roots: list):
    """造一个 PreToolUse hook：只放行落在 roots 里的源文件写操作。

    这道闸是必须的——``allowed_tools`` 只能决定"有没有 Edit 这个工具"，
    决定不了"这次改的是哪个文件"。而且 ``can_use_tool`` 回调在工具已被
    allowed_tools 放行时根本不会触发（SDK 自己会打 CanUseToolShadowedWarning）。
    """
    async def hook(input_data, _tool_use_id, _context):
        tool_input = (input_data or {}).get("tool_input") or {}
        path = str(tool_input.get("file_path") or "")
        if not path:
            reason = "没有给出 file_path。"
        elif not path.lower().endswith(WRITABLE_EXT):
            reason = f"只能改 .c/.h 源文件，不能改 {os.path.basename(path)}。"
        elif not _under(path, roots):
            reason = ("只能改工程 src/ 目录下的文件。ra/、ra_gen/、ra_cfg/ 是 "
                      "RASC 生成的配置代码，改了工程会坏，要改配置请让学生去 "
                      "RASC 里改。")
        else:
            logger.debug("写入放行 {}", path)
            return {}
        logger.warning("写入拦截 {} —— {}", path or "(无路径)", reason)
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}
    return hook


class Advisor(QThread):
    """常驻的 agent 会话。一个实例 = 一条会话。

    信号都在 UI 线程收：
        started_ok()                会话建好了
        text(str)                   回复的增量文本
        tool(icon, name, detail)    发起了一次工具调用
        edited(path)                改了某个文件（绝对路径）
        denied(name, reason)        某次工具调用被拒
        thinking()                  模型在思考（还没吐正文）
        turn_done(str)              这一轮结束，附一句用量摘要
        failed(str)                 出错了
    """

    started_ok = pyqtSignal()
    text = pyqtSignal(str)
    tool = pyqtSignal(str, str, str)
    edited = pyqtSignal(str)
    denied = pyqtSignal(str, str)
    thinking = pyqtSignal()
    turn_done = pyqtSignal(str)
    failed = pyqtSignal(str)

    _STOP = object()

    def __init__(self, cfg: AdvisorConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self._loop = None
        self._inbox = None
        self._pending = queue.Queue()   # 会话就绪前先攒着
        self._alive = False

    # ------------------------------------------------ UI 线程调用

    def ask(self, question: str):
        """把一个问题交给会话。可在会话就绪前调用。"""
        if self._loop and self._inbox and self._alive:
            logger.info("提问（会话已就绪）：{}", question[-120:])
            self._loop.call_soon_threadsafe(self._inbox.put_nowait, question)
        else:
            logger.info("提问（会话还没起来，先排队）：{}", question[-120:])
            self._pending.put(question)

    def shutdown(self):
        """结束会话并等线程退出。

        先把信号闸门关死：一轮还没跑完时线程是停不下来的（它卡在 SDK 的
        流式读取上），下面的 wait 会超时然后放弃它。被放弃的线程还会继续跑完
        这一轮，如果信号还连着，它吐的字和工具调用会画进**新会话**的对话区。
        """
        logger.info("请求结束会话")
        self.blockSignals(True)
        if self._loop and self._inbox:
            self._loop.call_soon_threadsafe(self._inbox.put_nowait, self._STOP)
        if not self.wait(5000):
            # 一轮还没跑完时 STOP 排在它后面，5 秒等不到很正常
            logger.warning("会话线程 5 秒内没退出，可能还有一轮在跑；强制丢弃")
            self._alive = False

    # ------------------------------------------------ 线程内部

    def run(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._serve())
        except Exception as e:                       # noqa: BLE001
            self.failed.emit(f"{type(e).__name__}: {e}")
        finally:
            self._alive = False
            if self._loop:
                self._loop.close()

    async def _serve(self):
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError:
            self.failed.emit("没有安装 claude-agent-sdk，请先 `uv pip install claude-agent-sdk`")
            return

        from claude_agent_sdk import HookMatcher

        self._inbox = asyncio.Queue()
        hooks = None
        if any(t in self.cfg.allowed_tools for t in ("Edit", "Write")):
            hooks = {"PreToolUse": [HookMatcher(
                matcher="Edit|Write|MultiEdit",
                hooks=[write_guard(self.cfg.write_roots)],
            )]}

        cli_path = bundled_cli_path()
        options = ClaudeAgentOptions(
            allowed_tools=self.cfg.allowed_tools,
            disallowed_tools=[t for t in self.cfg.blocked_tools
                              if t not in self.cfg.allowed_tools],
            system_prompt=self.cfg.system_prompt,
            cwd=self.cfg.project_root or None,
            model=self.cfg.model,
            max_turns=self.cfg.max_turns,
            max_budget_usd=self.cfg.max_budget_usd,
            include_partial_messages=True,      # 要流式增量
            setting_sources=None,               # 不读用户自己的 ~/.claude 配置
            mcp_servers=self.cfg.mcp_servers or {},
            hooks=hooks,
            env={
                "ANTHROPIC_BASE_URL": self.cfg.base_url,
                "ANTHROPIC_API_KEY": self.cfg.api_key,
            },
            **({"cli_path": cli_path} if cli_path else {}),
        )

        logger.info("开会话 model={} tools={} 写入目录={} cwd={}",
                 self.cfg.model, self.cfg.allowed_tools,
                 self.cfg.write_roots or "（只读）", self.cfg.project_root)
        async with ClaudeSDKClient(options=options) as client:
            self._alive = True
            logger.info("会话就绪")
            self.started_ok.emit()
            while not self._pending.empty():     # 补发就绪前攒下的问题
                self._inbox.put_nowait(self._pending.get())

            while True:
                item = await self._inbox.get()
                if item is self._STOP:
                    break
                try:
                    await self._one_turn(client, item)
                except Exception as e:           # noqa: BLE001
                    logger.exception("这一轮抛异常了")
                    self.failed.emit(f"{type(e).__name__}: {e}")

    async def _one_turn(self, client, question: str):
        from claude_agent_sdk import (AssistantMessage, ResultMessage,
                                      ToolUseBlock)

        t0 = time.time()
        logger.info("=== 一轮开始 ===")
        await client.query(question)
        saw_thinking = False
        produced = False        # 这一轮到底有没有产出（文字或工具调用）
        finished = False        # 收到 ResultMessage 了没
        last_seen = t0

        async for msg in client.receive_response():
            kind = type(msg).__name__
            # 两条消息之间隔得久 = 模型在憋一个大 block（思考或长 Edit 入参），
            # 界面上表现为"光标一直闪但什么都不出"。这行日志就是用来对账的。
            gap = time.time() - last_seen
            last_seen = time.time()
            if gap > 3:
                logger.debug("距上一条消息 {:.1f}s（{}）", gap, kind)

            # 流式增量：正文 token 和思考 token 走同一个事件，靠 delta.type 区分
            if kind == "StreamEvent":
                ev = getattr(msg, "event", None) or {}
                if ev.get("type") != "content_block_delta":
                    continue
                delta = ev.get("delta") or {}
                if delta.get("type") == "text_delta":
                    produced = True
                    self.text.emit(delta.get("text") or "")
                elif delta.get("type") == "thinking_delta" and not saw_thinking:
                    saw_thinking = True
                    logger.debug("模型开始思考（这段时间界面上只有光标在闪）")
                    self.thinking.emit()

            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        produced = True
                        logger.info("工具 {} {}", block.name,
                                    str(block.input)[:160])
                        self.tool.emit(
                            _TOOL_ICON.get(block.name, "🔍"),
                            _TOOL_LABEL.get(block.name, block.name),
                            _tool_detail(block.name, block.input),
                        )
                        if block.name in ("Edit", "Write", "MultiEdit"):
                            path = str((block.input or {}).get("file_path") or "")
                            if path:
                                self.edited.emit(path)

            elif isinstance(msg, ResultMessage):
                # 模型会声称"已完成"即使工具被拒了，所以以 SDK 的记录为准
                for d in (msg.permission_denials or []):
                    logger.warning("工具调用被拒 {}", d)
                    self.denied.emit(
                        _TOOL_LABEL.get(d.get("tool_name", ""), d.get("tool_name", "工具")),
                        str(d.get("message") or d.get("reason") or "调用被拒绝"),
                    )
                problem = _result_problem(msg, produced)
                if problem:
                    # 端点配错时 CLI 会安静地返回一个空的成功结果，
                    # 不报出来就只能看到"AI 什么都没说"
                    logger.error("这一轮有问题：{}", problem)
                    self.failed.emit(problem)
                logger.info("=== 一轮结束 === 墙上时间 {:.1f}s，轮次 {}，{}",
                            time.time() - t0, getattr(msg, "num_turns", "?"),
                            _usage_summary(msg))
                finished = True
                self.turn_done.emit(_usage_summary(msg))

        if not finished:
            # 没有 ResultMessage 就没有 turn_done，界面会一直停在"正在思考"
            logger.error("流结束了但没收到 ResultMessage，这一轮判为失败")
            self.failed.emit("和模型的连接中断了（没有收到本轮的结束消息）。"
                             "再问一次试试。")
            self.turn_done.emit("")


def _result_problem(result, produced: bool) -> str:
    """这一轮是不是出问题了；没问题返回空串。"""
    if getattr(result, "is_error", False):
        return str(getattr(result, "result", "") or getattr(result, "subtype", "未知错误"))
    api_err = getattr(result, "api_error_status", None)
    if api_err:
        return f"接口返回 {api_err}（检查 API 设置里的 base_url 与 key）"
    errors = getattr(result, "errors", None)
    if errors:
        return str(errors)[:300]
    if not produced:
        return ("这一轮没有任何输出。常见原因是 agent 端点不可用——"
                "它走的是 Anthropic 协议（.../anthropic），"
                "和普通对话的 .../v1 不是同一个地址。")
    return ""


def _usage_summary(result) -> str:
    """把一轮的耗时/费用压成一行，给气泡的页脚。"""
    parts = []
    ms = getattr(result, "duration_ms", None)
    if ms:
        parts.append(f"{ms / 1000:.1f}s")
    cost = getattr(result, "total_cost_usd", None)
    if cost:
        parts.append(f"${cost:.4f}")
    return " · ".join(parts)
