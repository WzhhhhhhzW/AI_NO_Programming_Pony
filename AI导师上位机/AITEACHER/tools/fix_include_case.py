"""把 #include "xxx.h" 的大小写改成和磁盘上真实文件名一致。

Windows 的文件系统不区分大小写，所以 ``#include "pwm.h"`` 配 ``PWM.h`` 能编过；
Linux / macOS 上直接 fatal error。这个脚本按真实文件名统一改写源码里的写法，
只动大小写，不动别的。

用法：
    python tools/fix_include_case.py <工程目录>            # 只报告，不改
    python tools/fix_include_case.py <工程目录> --write    # 实际写回

默认只扫工程的 src/ 目录：ra/、ra_gen/、ra_cfg/ 是 FSP 生成的，本来就一致，
而且改了会被下一次 RASC 生成覆盖。
"""

import os
import re
import sys

INCLUDE_RE = re.compile(r'(#\s*include\s*")([^"]+)(")')
SOURCE_EXT = (".c", ".h", ".cpp", ".hpp")


def build_name_map(scan_dirs):
    """小写文件名 -> 真实文件名。同名不同大小写的话保留第一个并告警。"""
    mapping = {}
    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.lower().endswith(SOURCE_EXT):
                continue
            key = name.lower()
            if key in mapping and mapping[key] != name:
                print(f"  ! 同时存在 {mapping[key]} 和 {name}，跳过这个名字")
                mapping[key] = None
            elif key not in mapping:
                mapping[key] = name
    return mapping


def fix_file(path, mapping, write):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        text = f.read()

    hits = []

    def repl(m):
        inc = m.group(2)
        head, tail = os.path.split(inc)
        real = mapping.get(tail.lower())
        if real and real != tail:
            hits.append((inc, os.path.join(head, real).replace("\\", "/")))
            return m.group(1) + os.path.join(head, real).replace("\\", "/") + m.group(3)
        return m.group(0)

    new_text = INCLUDE_RE.sub(repl, text)
    if hits and write:
        # newline="" 读写，保住工程原本的 CRLF
        with open(path, "w", encoding="utf-8", errors="replace", newline="") as f:
            f.write(new_text)
    return hits


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    project = os.path.abspath(argv[0])
    write = "--write" in argv[1:]

    src = os.path.join(project, "src")
    if not os.path.isdir(src):
        print(f"找不到 {src}")
        return 1

    mapping = build_name_map([src])
    total = 0
    for root, _dirs, files in os.walk(src):
        for name in sorted(files):
            if not name.lower().endswith(SOURCE_EXT):
                continue
            path = os.path.join(root, name)
            for old, new in fix_file(path, mapping, write):
                rel = os.path.relpath(path, project)
                print(f'  {rel}: #include "{old}"  ->  "{new}"')
                total += 1

    if total == 0:
        print("没有需要修正的 #include。")
    elif write:
        print(f"已修正 {total} 处。")
    else:
        print(f"发现 {total} 处，加 --write 才会写回。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
