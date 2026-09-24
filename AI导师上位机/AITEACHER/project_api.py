"""从工程的 src/ 里抽出"这台小马能干什么"，拼成一段给模型看的说明。

为什么不手写一份函数清单：队友改了代码清单就过时了，而模型照着过时的清单
去改会改错。这里全部从磁盘现读，永远和代码一致。

只扫 src/。``ra/`` ``ra_gen/`` ``ra_cfg/`` 是 RASC 生成的 FSP 代码，量大且
学生不该动，需要的时候让模型自己 Read 就行。
"""

import os
import re

# 形如：void Turn_Left();        //左转
_PROTO = re.compile(
    r"^\s*(?!#)(?:extern\s+)?"
    r"(?P<ret>[A-Za-z_]\w*(?:\s+\w+)*\s*\**)\s+"
    r"(?P<name>[A-Za-z_]\w*)\s*\((?P<args>[^;{)]*)\)\s*;"
    r"\s*(?://\s*(?P<note>.*))?$"
)
# 形如：#define Forward_mode 2      //前进
_DEFINE = re.compile(
    r"^\s*#\s*define\s+(?P<name>[A-Za-z_]\w*)\s+(?P<value>[^/\s][^/]*?)\s*"
    r"(?://\s*(?P<note>.*))?$"
)

MAX_PER_FILE = 40


def _lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().splitlines()
    except OSError:
        return []


def _headers(src_dir):
    return sorted(n for n in os.listdir(src_dir) if n.lower().endswith((".h", ".hpp")))


def _prototypes(path):
    out = []
    for line in _lines(path):
        m = _PROTO.match(line)
        if not m:
            continue
        name = m.group("name")
        if name in ("if", "while", "for", "switch", "return", "sizeof"):
            continue
        sig = f'{m.group("ret").strip()} {name}({m.group("args").strip()})'
        note = (m.group("note") or "").strip()
        out.append(f"  {sig};" + (f"   // {note}" if note else ""))
        if len(out) >= MAX_PER_FILE:
            break
    return out


def _defines(path):
    out = []
    for line in _lines(path):
        m = _DEFINE.match(line)
        if not m:
            continue
        note = (m.group("note") or "").strip()
        value = m.group("value").strip()
        if len(value) > 40:
            continue
        out.append(f'  #define {m.group("name")} {value}' + (f"   // {note}" if note else ""))
        if len(out) >= MAX_PER_FILE:
            break
    return out


def describe_api(project_root: str) -> str:
    """给初级模式的 system prompt 用的工程接口摘要。"""
    src = os.path.join(project_root, "src")
    if not os.path.isdir(src):
        return "（这个工程里没有 src/ 目录）"

    blocks = []
    for name in _headers(src):
        protos = _prototypes(os.path.join(src, name))
        if protos:
            blocks.append(f"src/{name} 里声明的函数：\n" + "\n".join(protos))

    # 模式号这类常量通常写在 .c 文件顶部而不是头文件里
    for name in sorted(n for n in os.listdir(src) if n.lower().endswith(".c")):
        defs = _defines(os.path.join(src, name))
        if defs:
            blocks.append(f"src/{name} 里的宏定义：\n" + "\n".join(defs))

    files = sorted(n for n in os.listdir(src)
                   if n.lower().endswith((".c", ".h", ".cpp", ".hpp")))
    head = "src/ 下的源文件：" + "、".join(files)
    if not blocks:
        return head
    return head + "\n\n" + "\n\n".join(blocks)
