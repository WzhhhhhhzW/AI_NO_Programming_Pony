"""高级模式的课程流程状态机。

刻意不依赖 Qt：课程推进的规则是纯逻辑，抽出来才好测、好改。
进度**不做持久化**——每次启动都从第 1 课开始。
"""

import re

import curriculum

# 只有很短且明确的指令才推进课程，避免"这一步我还没好"被误判
_ADVANCE_RE = re.compile(
    r"^\s*(下一步|下一课|继续|完成了|做完了|好了|搞定了?|配好了|写好了|建好了|ok|OK)"
    r"[\s，。!！~、.]*$"
)
_BACK_RE = re.compile(r"^\s*(上一步|上一课|返回上一步|回上一步)[\s，。!！~、.]*$")
_MAX_COMMAND_LEN = 15

# _handle_command 的返回值
NONE = "none"          # 不是导航指令，正常发给模型
MOVED = "moved"        # 已切换课程
AT_START = "at_start"  # 已在第一课
AT_END = "at_end"      # 已在最后一课


class LessonFlow:
    """持有"当前第几课"，并解释用户输入里的导航意图。"""

    def __init__(self):
        self.index = 0

    # ---- 状态 ----

    @property
    def total(self) -> int:
        return curriculum.TOTAL

    @property
    def lesson(self) -> dict:
        return curriculum.LESSONS[self.index]

    @property
    def title(self) -> str:
        return self.lesson["title"]

    @property
    def label(self) -> str:
        """工具条上显示的短标题。"""
        return f"{self.index + 1}/{self.total} · {self.title}"

    @property
    def header(self) -> str:
        """课程卡片的标题行。"""
        return f"第 {self.index + 1} 课 / 共 {self.total} 课 · {self.title}"

    @property
    def at_start(self) -> bool:
        return self.index <= 0

    @property
    def at_end(self) -> bool:
        return self.index >= self.total - 1

    # ---- 迁移 ----

    def goto(self, index: int) -> bool:
        """跳到指定课；返回是否真的发生了变化。"""
        new = curriculum.clamp(int(index))
        changed = new != self.index
        self.index = new
        return changed

    def prev(self) -> bool:
        return self.goto(self.index - 1)

    def next(self) -> bool:
        return self.goto(self.index + 1)

    def reset(self):
        self.index = 0

    # ---- 输入解释 ----

    def handle_command(self, text: str) -> str:
        """判断这句话是不是课程导航指令，是就执行。返回上面四个常量之一。"""
        if not text or len(text) > _MAX_COMMAND_LEN:
            return NONE
        if _ADVANCE_RE.match(text):
            if self.at_end:
                return AT_END
            self.next()
            return MOVED
        if _BACK_RE.match(text):
            if self.at_start:
                return AT_START
            self.prev()
            return MOVED
        return NONE
