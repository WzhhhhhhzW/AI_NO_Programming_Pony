"""给 agent 用的编译自检工具。

初级模式里 AI 会真的改代码，改完最好自己编一遍确认没写错。但**不给它 Bash**：
Windows 上要挂个 shell、路径带空格要引号、还能删文件。这里改成一个进程内的
MCP 工具，参数是空的，行为完全由我们决定——它只能触发一次编译，拿回结构化的
错误列表，别的什么都干不了。

编译逻辑和界面上的【一键编译】共用 builder.py 里那套（含 makefile.init 的
PATH 覆盖），不会出现"AI 说能编过、点按钮却编不过"。
"""

import os
import subprocess
import tempfile
import time

from loguru import logger

from builder import (BUILD_LOCK, build_path_value, find_debug_dir,
                     load_build_config, parse_diagnostics)

TIMEOUT_S = 240
MAX_ERRORS = 15


def check_file(project_root: str, rel_file: str) -> dict:
    """只检查一个文件，连 warning 一起回。

    不能靠 ``make``：增量编译对没改过的文件是"nothing to be done"，
    一条诊断都不会重新打印，模型会以为干干净净。

    做法是拿 FSP 自己生成的 ``Debug/src/xxx.o.in``——里面是这次构建用的
    完整编译参数——配 ``-fsyntax-only`` 重跑一遍。参数和真实构建**逐字
    一致**，不会出现"自检说没事、编译却报错"，而且不产出 .o，不打扰构建状态。
    """
    debug_dir = find_debug_dir(project_root)
    if not debug_dir:
        return {"ok": False, "summary": "找不到构建目录（工程下没有 Debug/makefile）。",
                "errors": [], "log_tail": ""}

    rel = rel_file.replace("\\", "/").lstrip("./")
    stem = os.path.splitext(rel)[0]
    args_file = os.path.join(debug_dir, stem + ".o.in")
    if not os.path.isfile(args_file):
        return {"ok": False,
                "summary": (f"没有 {rel} 的编译参数（{stem}.o.in 不存在）。"
                            "先不带参数调一次 compile_project 整体编译一遍再来。"),
                "errors": [], "log_tail": ""}

    cfg = load_build_config()
    path_value = build_path_value(debug_dir, cfg["toolchain_bin"], cfg["make_path"])
    env = os.environ.copy()
    env["PATH"] = path_value
    gcc = "arm-none-eabi-gcc.exe" if os.name == "nt" else "arm-none-eabi-gcc"
    logger.info("AI 单文件自检 {}", rel)
    # .o.in 里带着 -MMD -MF"src/xxx.d"，-fsyntax-only 照样会写这个依赖文件，
    # 而且编译失败时写出来的是残缺的一份，会削弱 make 的头文件依赖跟踪。
    # 后面再给一个 -MF 就能覆盖前面那个（gcc 取最后一个），把它引到临时文件。
    dep_fd, dep_path = tempfile.mkstemp(suffix=".d")
    os.close(dep_fd)
    try:
        proc = subprocess.run(
            [gcc, "@" + os.path.relpath(args_file, debug_dir),
             "-fsyntax-only", "-MF" + dep_path],
            cwd=debug_dir, env=env, timeout=60,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "summary": f"单文件检查跑不起来：{e}",
                "errors": [], "log_tail": ""}
    finally:
        try:
            os.unlink(dep_path)
        except OSError:
            pass

    diagnostics = parse_diagnostics((proc.stdout or "").splitlines(),
                                    debug_dir, project_root)[:MAX_ERRORS]
    bad = sum(1 for d in diagnostics if d["kind"] != "warning")
    warn = len(diagnostics) - bad
    if not diagnostics:
        summary = f"{rel} 没有错误也没有警告。"
    else:
        summary = f"{rel}：{bad} 处错误、{warn} 处警告。"
    logger.info("单文件自检结束：{}", summary)
    return {"ok": bad == 0, "summary": summary, "errors": diagnostics, "log_tail": ""}


def compile_once(project_root: str) -> dict:
    """整个工程编一次，返回 {ok, summary, errors, log_tail}。

    只回 error：这个工程本来就带着几十条 warning（oled.c 的 signedness
    之类），全倒给模型会把它的注意力冲散。想看警告用 check_file()。
    """
    debug_dir = find_debug_dir(project_root)
    if not debug_dir:
        return {"ok": False, "summary": "找不到构建目录（工程下没有 Debug/makefile）。",
                "errors": [], "log_tail": ""}

    logger.info("AI 触发编译自检 {}", debug_dir)
    started = time.time()
    if not BUILD_LOCK.acquire(blocking=False):
        logger.warning("编译锁被占，拒绝这次自检")
        return {"ok": False, "summary": "上位机正在编译，稍后再试。",
                "errors": [], "log_tail": ""}
    try:
        cfg = load_build_config()
        env = os.environ.copy()
        path_value = build_path_value(debug_dir, cfg["toolchain_bin"], cfg["make_path"])
        env["PATH"] = path_value
        try:
            proc = subprocess.run(
                # -k：出错也继续编别的文件，一次把所有错误拿全
                [cfg["make_path"], f"PATH={path_value}", "-j4", "-k", "all"],
                cwd=debug_dir, env=env, timeout=TIMEOUT_S,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except FileNotFoundError:
            return {"ok": False, "summary": f"找不到 make：{cfg['make_path']}",
                    "errors": [], "log_tail": ""}
        except subprocess.TimeoutExpired:
            return {"ok": False, "summary": f"编译超过 {TIMEOUT_S} 秒被中止。",
                    "errors": [], "log_tail": ""}

        out = proc.stdout or ""
        # 和界面上的问题列表共用同一份解析，省得两边对不上
        diagnostics = parse_diagnostics(out.splitlines(), debug_dir, project_root)
        ok = proc.returncode == 0
        errors = [d for d in diagnostics if d["kind"] != "warning"][:MAX_ERRORS]
        if ok:
            summary = "编译通过。"
        elif errors:
            summary = f"编译失败，{len(errors)} 处错误。"
        else:
            summary = f"编译失败（退出码 {proc.returncode}），但没解析出编译器错误行。"
        logger.info("编译自检结束 {:.1f}s：{}", time.time() - started, summary)
        return {"ok": ok, "summary": summary, "errors": errors,
                "log_tail": "\n".join(out.splitlines()[-25:])}
    finally:
        BUILD_LOCK.release()


def format_result(result: dict) -> str:
    """压成一段给模型读的纯文本。"""
    lines = [result["summary"]]
    for e in result["errors"]:
        tag = "警告" if e.get("kind") == "warning" else "错误"
        lines.append(f'{tag} {e["file"]}:{e["line"]}: {e["message"]}')
    if not result["ok"] and not result["errors"] and result["log_tail"]:
        lines.append("--- 日志末尾 ---")
        lines.append(result["log_tail"])
    return "\n".join(lines)


def make_server(project_root: str):
    """构造一个只含 compile_project 的进程内 MCP server。

    返回 (server_config, 工具全名)；SDK 会把工具名映射成
    ``mcp__<server 名>__<工具名>``，allowed_tools 里要写全名。
    """
    from claude_agent_sdk import create_sdk_mcp_server, tool

    @tool("compile_project",
          "编译当前工程并做静态检查，返回编译器报的问题（文件:行号:说明）。"
          "不带参数 = 检查整个工程，只回错误；"
          "带 file 参数（例如 src/action.c）= 只看这个文件，连警告一起回，"
          "改完某个文件想自查时用这个。",
          {"file": str})
    async def compile_project(args):
        import asyncio
        only = str((args or {}).get("file") or "").strip()
        if only:
            result = await asyncio.to_thread(check_file, project_root, only)
        else:
            result = await asyncio.to_thread(compile_once, project_root)
        return {"content": [{"type": "text", "text": format_result(result)}]}

    server = create_sdk_mcp_server("horse", "1.0.0", [compile_project])
    return server, "mcp__horse__compile_project"
