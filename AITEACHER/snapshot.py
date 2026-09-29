"""AI 改代码前后的 src/ 快照、改动 diff、一键撤销。

为什么要快照：现场演示时 AI 一次可能改好几个地方，改坏了没有退路是不行的。
``src/`` 通常不到 100KB，整目录拷贝一次十几毫秒，比任何增量方案都可靠。

为什么 diff 是拿快照和磁盘现算，而不是用模型 ``Edit`` 调用里报的 old/new：
现算的是**磁盘上的真实结果**。模型一轮改三处也能一次展示完，而且模型说改了
实际没改的情况一眼就看得出来。

快照放在配置目录（Windows 是 ``%APPDATA%\\RenesasHorseAI``），不放工程里——
放工程里会出现在文件树、会被 e2 studio 当源码扫、发给别人时还带着。
"""

import difflib
import os
import shutil
import time
from dataclasses import dataclass, field

from loguru import logger

from config import _CONFIG_DIR

SNAP_ROOT = os.path.join(_CONFIG_DIR, "snapshots")
KEEP = 5                                     # 每个工程只留最近几份
SOURCE_EXT = (".c", ".h", ".cpp", ".hpp")
CONTEXT = 2                                  # diff 上下文行数


@dataclass
class Row:
    """diff 里的一行。``kind`` 是 ctx / add / del / gap。"""
    kind: str
    old: int | None
    new: int | None
    text: str


@dataclass
class FileDiff:
    rel_path: str
    abs_path: str
    added: int = 0
    removed: int = 0
    rows: list[Row] = field(default_factory=list)
    first_line: int = 1          # 新文件里第一处改动的行号，用于编辑器跳转
    note: str = ""               # "新增文件" / "删除文件"


def _read_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            return f.read().splitlines()
    except OSError:
        return None


def _diff_rows(old_lines, new_lines):
    """生成带上下文的 diff 行列表。

    分两步，避免在一个循环里同时处理"折叠"和"行号"：
      1. 先把全文按 opcode 摊平成 Row（每行都有准确的新旧行号）
      2. 再把离改动超过 CONTEXT 行的部分折成一个 gap 行

    不用 ``unified_diff`` 是因为它输出的是文本，还得再解析回行号。
    """
    sm = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)

    flat: list[Row] = []
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                flat.append(Row("ctx", i1 + k + 1, j1 + k + 1, old_lines[i1 + k]))
            continue
        for k in range(i1, i2):
            flat.append(Row("del", k + 1, None, old_lines[k]))
            removed += 1
        for k in range(j1, j2):
            flat.append(Row("add", None, k + 1, new_lines[k]))
            added += 1

    changed = [i for i, r in enumerate(flat) if r.kind != "ctx"]
    if not changed:
        return [], 0, 0, 1

    keep = set()
    for i in changed:
        keep.update(range(max(0, i - CONTEXT), min(len(flat), i + CONTEXT + 1)))

    rows: list[Row] = []
    for i, row in enumerate(flat):
        if i in keep:
            rows.append(row)
        elif rows and rows[-1].kind != "gap":
            rows.append(Row("gap", None, None, ""))

    first = next((r.new for r in flat if r.kind == "add" and r.new), None)
    if first is None:
        # 纯删除：跳到被删位置的上一行
        idx = changed[0]
        prev = next((flat[k].new for k in range(idx, -1, -1) if flat[k].new), 1)
        first = prev
    return rows, added, removed, max(first, 1)


MAX_ROWS = 120          # 单个文件在对话区里最多铺这么多行


def to_payload(d: "FileDiff") -> dict:
    """转成对话区网页那边 addDiff() 认的结构。"""
    rows = d.rows
    if len(rows) > MAX_ROWS:
        rows = rows[:MAX_ROWS] + [Row("gap", None, None, "")]
    return {
        "path": d.rel_path, "abs": d.abs_path, "line": d.first_line,
        "added": d.added, "removed": d.removed, "note": d.note,
        "rows": [{"kind": r.kind, "old": r.old, "new": r.new, "text": r.text}
                 for r in rows],
    }


def added_lines(d: "FileDiff") -> list:
    """新文件里被加/改过的行号，用来在编辑器里铺底色。"""
    return [r.new for r in d.rows if r.kind == "add" and r.new]


class SrcSnapshot:
    """一个工程的 src/ 快照。UI 侧持有一个实例。"""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.src = os.path.join(project_root, "src")
        self.snap_dir = ""

    # ---- 拍快照 ----

    def take(self) -> bool:
        """在 AI 动手之前调用。拍不成返回 False（调用方应当拒绝改码）。"""
        if not os.path.isdir(self.src):
            return False
        name = os.path.basename(self.project_root.rstrip(os.sep)) or "project"
        dest = os.path.join(SNAP_ROOT, name, time.strftime("%Y%m%d-%H%M%S"))
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.exists(dest):                 # 同一秒内连开两轮
                dest += f"-{int(time.time() * 1000) % 1000:03d}"
            shutil.copytree(self.src, dest)
        except OSError:
            logger.exception("拍快照失败，本轮不允许改代码")
            return False
        self.snap_dir = dest
        self._prune(os.path.dirname(dest))
        logger.info("已给 src/ 拍快照 -> {}", dest)
        return True

    @staticmethod
    def _prune(parent):
        try:
            snaps = sorted(d for d in os.listdir(parent)
                           if os.path.isdir(os.path.join(parent, d)))
        except OSError:
            return
        for old in snaps[:-KEEP]:
            shutil.rmtree(os.path.join(parent, old), ignore_errors=True)

    # ---- 比较 ----

    @property
    def has_snapshot(self) -> bool:
        return bool(self.snap_dir) and os.path.isdir(self.snap_dir)

    def _source_files(self, root):
        out = {}
        for base, _dirs, files in os.walk(root):
            for name in files:
                if name.lower().endswith(SOURCE_EXT):
                    full = os.path.join(base, name)
                    out[os.path.relpath(full, root).replace("\\", "/")] = full
        return out

    def changes(self) -> list[FileDiff]:
        """快照之后 src/ 里发生的所有改动。没快照就返回空。"""
        if not self.has_snapshot:
            return []
        before = self._source_files(self.snap_dir)
        after = self._source_files(self.src)

        result = []
        for rel in sorted(set(before) | set(after)):
            old = _read_lines(before[rel]) if rel in before else []
            new = _read_lines(after[rel]) if rel in after else []
            if old is None or new is None or old == new:
                continue
            note = ""
            if rel not in before:
                note = "新增文件"
            elif rel not in after:
                note = "删除文件"
            rows, added, removed, first = _diff_rows(old, new)
            result.append(FileDiff(
                rel_path="src/" + rel,
                abs_path=after.get(rel, ""),
                added=added, removed=removed, rows=rows,
                first_line=first, note=note,
            ))
        return result

    # ---- 撤销 ----

    def restore(self) -> tuple[bool, str]:
        """把 src/ 还原成快照的样子。返回 (成功, 说明)。"""
        if not self.has_snapshot:
            logger.warning("要回退但没有快照")
            return False, "没有可回退的快照。"
        # 防呆：只允许作用在名字确实是 src 的目录上
        if os.path.basename(self.src.rstrip(os.sep)) != "src":
            return False, f"目标目录不是 src：{self.src}"
        try:
            shutil.rmtree(self.src)
            shutil.copytree(self.snap_dir, self.src)
        except OSError as e:
            logger.exception("回退失败")
            return False, f"回退失败：{e}"
        logger.info("已从 {} 回退 src/", self.snap_dir)
        return True, "已还原到这次修改之前的状态。"
