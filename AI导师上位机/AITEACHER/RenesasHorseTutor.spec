# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包脚本。

    pyinstaller RenesasHorseTutor.spec --noconfirm

**必须在目标平台上打包**（要发 Windows 就得在 Windows 上跑），PyInstaller
不做交叉编译。

三个坑，都在下面处理了：

1. **onedir，不要 onefile。** claude-agent-sdk 自带一个 300MB 的 CLI，
   onefile 每次启动都要把它解压到临时目录，开一次要等十几秒，而且临时目录
   路径每次都变。onedir 是一个文件夹，双击 exe 秒开。
2. **claude-agent-sdk 的 `_bundled/claude(.exe)` 不会被自动收进去**——它是
   包里的二进制而不是 .py。SDK 找它的方式是 `Path(__file__)/../../../_bundled`，
   所以必须原样放在 `claude_agent_sdk/_bundled/` 下面。
3. **QtWebEngine** 要带 QtWebEngineProcess、.pak 资源、ICU 数据和翻译。
   PyQt6 的官方 hook 会处理，这里再显式 collect 一次兜底。
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

APP_NAME = "RenesasHorseTutor"
IS_WIN = sys.platform.startswith("win")

# ---- claude-agent-sdk 自带的 CLI ----------------------------------------
import claude_agent_sdk  # noqa: E402

SDK_DIR = Path(claude_agent_sdk.__file__).parent
CLI_NAME = "claude.exe" if IS_WIN else "claude"
CLI_PATH = SDK_DIR / "_bundled" / CLI_NAME
if not CLI_PATH.exists():
    raise SystemExit(
        f"找不到 {CLI_PATH}。\n"
        "claude-agent-sdk 的 wheel 是分平台的，要在目标平台上重新安装：\n"
        "  uv pip install --force-reinstall claude-agent-sdk"
    )
# 放进 binaries 而不是 datas：datas 不保留可执行位（Windows 无所谓，
# 但在 Linux/mac 上打包时这一条是必须的）
sdk_binaries = [(str(CLI_PATH), "claude_agent_sdk/_bundled")]
sdk_datas = collect_data_files("claude_agent_sdk")

# ---- QtWebEngine ---------------------------------------------------------
web_datas, web_binaries, web_hidden = collect_all("PyQt6.QtWebEngineCore")

# ---- 随程序分发的工具 ----------------------------------------------------
tool_datas = []
for sub in ("rfp-cli", "templates", "toolchain", "make"):
    src = os.path.join("tools", sub)
    if os.path.isdir(src):
        tool_datas.append((src, f"tools/{sub}"))

a = Analysis(
    ["main_host_computer.py"],
    pathex=[],
    binaries=sdk_binaries + web_binaries,
    datas=tool_datas + sdk_datas + web_datas,
    hiddenimports=[
        "PyQt6.Qsci",                 # QScintilla，只在 code_editor 里 from ... import
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "loguru",
        "mcp",                        # SDK 的进程内 MCP server 要用
        "anyio",
        "pygments.formatters.html",   # markdown_render 动态取 formatter/style
        "pygments.styles.monokai",
        "pygments.styles.friendly",
        "pygments.lexers.c_cpp",
    ] + web_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "PIL", "pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,            # ← onedir 的关键：二进制交给 COLLECT
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                        # UPX 压 Qt 的 dll 经常压出启动崩溃
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)
