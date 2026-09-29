"""工程目录的判定与描述。

"学生在做哪个工程"由主窗口的 ``CoderUI.project_root`` 唯一回答——它在
【打开工程】时确定。这里只提供判定和描述，不再有任何从别处推断的逻辑。

判定依据是 ``configuration.xml``：这是 RA 工程的根标志。

``describe()`` 的输出会写进 agent 的 system prompt：实测只给 ``cwd``
不够，模型会去猜路径（第一次跑时它去读了 ``~/src/action.c``）。
"""

import os

MARKER = "configuration.xml"
_MAX_WALK_UP = 6


def is_project_root(path: str) -> bool:
    return bool(path) and os.path.isfile(os.path.join(path, MARKER))


def walk_up_for_root(start: str) -> str:
    """从一个文件或目录往上找工程根，找不到返回空串。"""
    if not start:
        return ""
    cur = start if os.path.isdir(start) else os.path.dirname(start)
    for _ in range(_MAX_WALK_UP):
        if is_project_root(cur):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return ""


def describe(root: str) -> str:
    """给 system prompt 用的一段工程说明。"""
    if not root:
        return "学生当前没有打开任何工程。"
    src = os.path.join(root, "src")
    files = []
    if os.path.isdir(src):
        files = sorted(f for f in os.listdir(src) if f.endswith((".c", ".h")))
    listing = "、".join(files) if files else "（src 目录为空或不存在）"
    # 工程特有的知识（外设怎么接的、哪个函数是空壳、屏幕要不要刷新）写在工程
    # 自己的 README 里，跟着工程走，不塞进上位机代码
    readme = ""
    if os.path.isfile(os.path.join(root, "README.md")):
        readme = ("工程根目录有 README.md，写着这个工程特有的硬件参数和已知的坑，"
                  "动手之前先读它。\n")
    return (
        f"学生的 e2 studio 工程根目录是：{root}\n"
        f"该目录下有 {MARKER}（FSP 配置）和 src/ 源码目录。\n"
        f"{readme}"
        f"src/ 里现有文件：{listing}\n"
        f"读取文件时请使用这个根目录下的路径，不要猜测其它位置。"
    )
