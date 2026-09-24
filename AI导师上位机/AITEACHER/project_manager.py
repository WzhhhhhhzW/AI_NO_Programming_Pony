"""
Project creation and management for Renesas RA projects.

Wraps e2 studio / RASC tooling: the Python app creates the project skeleton
(directories, configuration.xml, FSP library, linker scripts, makefiles) and
then optionally launches RASC for interactive code generation.

Templates are bundled under ``tools/templates/`` and selected by teaching
project type (LED, Servo, OLED, Robohorse).
"""
import os
import shutil
import subprocess
import sys
import zipfile
from typing import Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal

from environment import (
    find_e2studio,
    find_e2studio_root,
    find_e2studioc,
    find_rasc,
    find_rasc_or_e2studio,
    find_toolchain_bin,
    find_make,
    is_toolchain_ready,
)


# --------------- template registry ---------------

TEMPLATE_REGISTRY: dict = {
    "LED_Test": {
        "display_name": "LED 点灯工程",
        "description": (
            "学习 GPIO 输出控制板载 LED 闪烁——嵌入式世界的 Hello World。\n"
            "已预配置: XTAL 12MHz → PLL ×30 → 180MHz, SWD (P300/P108), "
            "板载 LED 引脚 P111 配置为输出。"
        ),
        "device": "R7FA4M2AD3CFL",
        "fsp_version": "6.0.0",
    },
    "Servo_Test": {
        "display_name": "舵机控制工程",
        "description": (
            "学习 GPT 定时器 PWM 输出控制舵机——理解占空比与角度控制。\n"
            "已预配置: 时钟系统, SWD 调试口, GPT Channel 4 (Tail) 在 P302 输出 50Hz PWM。"
        ),
        "device": "R7FA4M2AD3CFL",
        "fsp_version": "6.0.0",
    },
    "OLED_Test": {
        "display_name": "OLED 显示工程",
        "description": (
            "学习 I2C 总线通信驱动 OLED 屏幕——从底层协议到像素显示。\n"
            "已预配置: 时钟系统, SWD, I2C Master Ch0 (SCL=P408, SDA=P407, 从机 0x3C, Fast-mode 400kHz)。"
        ),
        "device": "R7FA4M2AD3CFL",
        "fsp_version": "6.0.0",
    },
    "Robohorse": {
        "display_name": "完整机器马工程",
        "description": (
            "集成全部外设——5路PWM + UART蓝牙 + I2C OLED，打造完整的蓝牙遥控四足机器人。\n"
            "已预配置: 时钟, SWD, GPT Ch1~Ch4 (4腿+尾巴), UART Ch0 (蓝牙), I2C Ch0 (OLED)。"
        ),
        "device": "R7FA4M2AD3CFL",
        "fsp_version": "6.0.0",
    },
}


def get_template_dir() -> str:
    """Absolute path to the bundled templates directory.

    In dev mode this is ``<project>/tools/templates/``.
    When frozen (PyInstaller) it is ``<MEIPASS>/tools/templates/``.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "tools", "templates")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "templates")


def list_templates() -> list[dict]:
    """Return available templates that are actually present on disk."""
    tmpl_dir = get_template_dir()
    available = []
    for name, info in TEMPLATE_REGISTRY.items():
        candidate = os.path.join(tmpl_dir, name)
        if os.path.isdir(candidate) and os.path.exists(
            os.path.join(candidate, "configuration.xml")
        ):
            available.append({"name": name, **info})
    return available


# --------------- validation ---------------

def validate_workspace(workspace_dir: str) -> tuple[bool, str]:
    """Check that *workspace_dir* is usable for a new project.

    Returns (ok, reason).
    """
    if not workspace_dir:
        return False, "请选择工作空间目录。"

    # ASCII-only guard — GCC toolchain chokes on CJK paths
    if any(ord(ch) > 127 for ch in workspace_dir):
        return False, (
            "工作空间路径包含中文字符或特殊字符，编译工具链 (GCC) 无法正确处理。\n"
            "请选择纯英文路径，例如 D:\\e2s_workspace。"
        )

    # Must exist
    if not os.path.isdir(workspace_dir):
        return False, f"工作空间目录不存在: {workspace_dir}"

    # Write permission check
    if not os.access(workspace_dir, os.W_OK):
        return False, f"工作空间目录没有写入权限: {workspace_dir}"

    # Disk free-space check (arbitrary safety margin: 100 MB)
    try:
        usage = shutil.disk_usage(workspace_dir)
        if usage.free < 100 * 1024 * 1024:
            return False, "磁盘空间不足，至少需要 100MB 可用空间。"
    except Exception:
        pass  # can't check — proceed anyway

    return True, "OK"


def validate_project_name(workspace_dir: str, project_name: str) -> tuple[bool, str]:
    """Check *project_name* is valid and doesn't already exist."""
    if not project_name.strip():
        return False, "请输入工程名称。"
    # Valid characters
    if any(ch in r'\/:*?"<>|' for ch in project_name):
        return False, "工程名称包含非法字符 (\\ / : * ? \" < > |)。"
    if any(ord(ch) > 127 for ch in project_name):
        return False, "工程名称请使用英文或数字（路径编码兼容性）。"
    target = os.path.join(workspace_dir, project_name)
    if os.path.exists(target):
        return False, f"目标路径已存在: {target}\n请更换工程名称或工作空间。"
    return True, "OK"


# --------------- project creation ---------------

def _fixup_makefile(makefile_path: str, new_project_dir: str, new_project_name: str):
    """Update hardcoded paths in Debug/makefile and all subdir.mk files.

    e2 studio bakes absolute ``-I`` and ``-L`` paths and the project
    name into the generated build files.  This rewrites them for the
    new project location and name.
    """
    import re
    debug_dir = os.path.dirname(makefile_path)
    new_dir_fwd = new_project_dir.replace("\\", "/")

    # --- Discover the old project name from subdir.mk files ---
    old_project_name = None
    old_project_dir = None
    for root, dirs, files in os.walk(debug_dir):
        for fname in files:
            if fname != "subdir.mk":
                continue
            with open(os.path.join(root, fname), "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            # Extract old project name from SREC/MAP variable
            m = re.search(r'(?:SREC|MAP)\s*\+=\s*\\\s*\n?(\w+)\.(?:srec|map)', sc)
            if m:
                old_project_name = m.group(1)
            # Extract old project dir from -I or -L paths
            for m in re.finditer(r'-[IL]\s*"([^"]+)"', sc):
                path = m.group(1).replace("\\", "/")
                # Walk up to find the project root (parent of src, ra_gen, etc.)
                for seg in ("/src", "/ra_gen", "/ra_cfg", "/ra/fsp", "/script"):
                    if path.endswith(seg):
                        old_project_dir = path[: -len(seg)]
                        break
                if old_project_dir:
                    break
            if old_project_dir and old_project_name:
                break
        if old_project_dir and old_project_name:
            break

    def swap_dir(text: str) -> str:
        """把旧工程目录换成新的。

        e2 studio 在不同文件里用不同的斜杠写法：subdir.mk 的 ``-I`` 是正斜杠，
        makefile 的 ``-L`` 是双反斜杠（make 里 ``\\`` 要转义）。三种都换。
        统一写成正斜杠——Windows 上的 make 和 gcc 一样认。
        """
        if not old_project_dir:
            return text
        fwd = old_project_dir.replace("\\", "/")
        for old in (fwd, fwd.replace("/", "\\\\"), fwd.replace("/", "\\")):
            text = text.replace(old, new_dir_fwd)
        return text

    def swap_name(text: str) -> str:
        """把产物名里的旧工程名换成新的。

        ``.srec`` 是烧录用的那个，务必在列表里——漏了它会编出一个叫旧工程名
        的固件（能烧，但名字对不上，看着像烧错了）。
        """
        if not old_project_name or old_project_name == new_project_name:
            return text
        for ext in (".elf", ".hex", ".srec", ".map", ".siz"):
            text = text.replace(old_project_name + ext, new_project_name + ext)
        return text

    # makefile.init 里那串 `export PATH=<队友机器上的绝对路径>` 不在这儿处理:
    # 构建时用 `make PATH=...` 以命令行变量的形式覆盖它（优先级高于 makefile
    # 里的赋值，见 builder.build_path_value），而且 e2 studio 每次构建都会重新
    # 生成这个文件，改了也会被覆盖回去。同文件里的 TCINSTALL / TC_VERSION /
    # GCC_VERSION 没有任何 makefile 引用，是惰性数据。

    # --- 1. Fix the main makefile ---
    if os.path.exists(makefile_path):
        with open(makefile_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        content = swap_name(swap_dir(content))
        with open(makefile_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(content)

    # --- 2. Fix all subdir.mk files ---
    for root, dirs, files in os.walk(debug_dir):
        for fname in files:
            if fname != "subdir.mk":
                continue
            sub_path = os.path.join(root, fname)
            with open(sub_path, "r", encoding="utf-8", errors="replace") as f:
                sc = f.read()
            sc = swap_name(swap_dir(sc))
            with open(sub_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(sc)


def _fix_include_case(src_dir: str):
    """把 src/ 里 #include 的大小写改成和真实文件名一致。失败不影响建工程。"""
    if not os.path.isdir(src_dir):
        return
    try:
        from tools.fix_include_case import SOURCE_EXT, build_name_map, fix_file
        mapping = build_name_map([src_dir])
        for root, _dirs, files in os.walk(src_dir):
            for name in files:
                if name.lower().endswith(SOURCE_EXT):
                    fix_file(os.path.join(root, name), mapping, write=True)
    except Exception:
        pass


def create_project(
    template_name: str,
    workspace_dir: str,
    project_name: str,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> tuple[bool, str]:
    """Create a new RA project from a template.

    Copies the template skeleton (including pre-generated ``ra_gen/``)
    to ``workspace_dir/project_name``.

    Args:
        template_name: One of the keys in *TEMPLATE_REGISTRY*.
        workspace_dir: Parent directory where the project folder is created.
        project_name: Folder name for the new project.
        progress_callback: Optional ``(status_message, percent)`` hook.

    Returns:
        (success, detail) — on success *detail* is the project directory path.
    """
    tmpl_dir = get_template_dir()
    source = os.path.join(tmpl_dir, template_name)

    # --- validate inputs ---
    if not os.path.isdir(source):
        return False, f"模板目录不存在: {source}"

    ok, msg = validate_workspace(workspace_dir)
    if not ok:
        return False, msg

    ok, msg = validate_project_name(workspace_dir, project_name)
    if not ok:
        return False, msg

    target = os.path.join(workspace_dir, project_name)

    # --- copy ---
    def _report(msg: str, pct: int):
        if progress_callback:
            progress_callback(msg, pct)

    try:
        _report("正在复制 FSP 框架库...", 10)
        shutil.copytree(source, target)
        _report("项目骨架复制完成", 90)

        # Remove any leftover IDE metadata we don't want to propagate
        # Note: Debug/ is KEPT — it contains the makefile and build config
        for pattern in [".settings", "JLinkLog.log"]:
            p = os.path.join(target, pattern)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.isfile(p):
                os.remove(p)

        # Rename .launch debug config to match new project name
        for fname in os.listdir(target):
            if fname.endswith("Debug_Flat.launch"):
                old = os.path.join(target, fname)
                new = os.path.join(target, f"{project_name} Debug_Flat.launch")
                if old != new:
                    os.rename(old, new)
                break

        # Ensure fsp.ld exists in Debug/ (linker looks for it in CWD)
        script_ld = os.path.join(target, "script", "fsp.ld")
        debug_ld = os.path.join(target, "Debug", "fsp.ld")
        if os.path.exists(script_ld) and not os.path.exists(debug_ld):
            shutil.copy2(script_ld, debug_ld)

        # 模板是在 Windows 上生成的，那边文件系统不区分大小写，
        # #include "pwm.h" 配 PWM.h 照样编得过；Linux/macOS 上直接 fatal error。
        # 这里按磁盘上的真实文件名统一一遍，只动大小写。
        _report("正在统一 #include 大小写...", 80)
        _fix_include_case(os.path.join(target, "src"))

        # Fix up hardcoded paths in Debug/makefile
        _report("正在修正编译路径...", 85)
        _fixup_makefile(
            os.path.join(target, "Debug", "makefile"),
            target,
            project_name,
        )

        # Verify essential files exist
        missing = []
        for essential in ["configuration.xml", "ra", "ra_gen", "src", "Debug"]:
            if not os.path.exists(os.path.join(target, essential)):
                missing.append(essential)
        # Also check Debug has a makefile
        if not os.path.exists(os.path.join(target, "Debug", "makefile")):
            missing.append("Debug/makefile")
        if missing:
            _report("清理中...", 95)
            shutil.rmtree(target, ignore_errors=True)
            return False, f"模板不完整，缺少: {', '.join(missing)}"

        _report("工程创建完成", 100)
        return True, target

    except PermissionError as e:
        _report("权限不足", 0)
        shutil.rmtree(target, ignore_errors=True)
        return False, f"写入被拒绝: {e}"
    except OSError as e:
        _report("创建失败", 0)
        shutil.rmtree(target, ignore_errors=True)
        return False, f"创建失败: {e}"


# --------------- RASC / e2 studio interaction ---------------

def open_project_in_rasc(project_dir: str) -> tuple[bool, str]:
    """Open *project_dir* in RA Smart Configurator for FSP configuration.

    Launches standalone rasc.exe if available, otherwise falls back to
    opening the project in e2studio.

    Returns (launched, detail_message).
    """
    config_xml = os.path.join(project_dir, "configuration.xml")
    if not os.path.exists(config_xml):
        return False, f"找不到 configuration.xml: {config_xml}"

    # Prefer standalone RASC
    rasc = find_rasc()
    if rasc:
        try:
            subprocess.Popen([rasc, "--compiler", "GCC", config_xml])
            return True, "已打开 RA Smart Configurator。"
        except Exception as e:
            return False, f"启动 RASC 失败: {e}"

    # Fallback: e2studio
    e2s = find_e2studio()
    if e2s:
        try:
            # e2studio can open a project by passing the project directory
            subprocess.Popen([e2s, project_dir])
            return True, "已打开 e2 studio。请在 FSP Configuration 透视图中查看。"
        except Exception as e:
            return False, f"启动 e2 studio 失败: {e}"

    return False, (
        "未找到 RASC 或 e2 studio。\n"
        "请从 https://www.renesas.cn/zh/software-tool/ra-smart-configurator 下载安装。"
    )


def build_with_eclipsec(project_dir: str) -> tuple[bool, str]:
    """Build *project_dir* using e2 studio's headless builder (eclipsec/e2studioc).

    This is an alternative to the make-based build in builder.py.
    Requires e2 studio installation.

    Returns (success, detail_message).
    """
    eclipsec = find_e2studioc()
    if not eclipsec:
        # Some older installs use 'eclipsec.exe' instead of 'e2studioc.exe'
        root = find_e2studio_root()
        if root:
            candidate = os.path.join(root, "eclipse", "eclipsec.exe")
            if os.path.exists(candidate):
                eclipsec = candidate
    if not eclipsec:
        return False, "未找到 e2 studio console 版本 (e2studioc.exe)。无法使用 headless 编译。"

    # Ensure eclipsec.ini exists (copy from e2studio.ini)
    ini_dir = os.path.dirname(eclipsec)
    e2s_ini = os.path.join(ini_dir, "e2studio.ini")
    ec_ini = os.path.join(ini_dir, "eclipsesc.ini") if "eclipsec" in eclipsec else os.path.join(ini_dir, "e2studioc.ini")
    # Actually Renesas uses e2studioc.exe, and the ini should be e2studio.ini copied
    # Check the actual naming convention
    for ini_name in ["e2studioc.ini", "eclipsec.ini", "eclipse.ini"]:
        if not os.path.exists(os.path.join(ini_dir, ini_name)):
            if os.path.exists(e2s_ini):
                shutil.copy2(e2s_ini, os.path.join(ini_dir, ini_name))

    workspace_dir = os.path.dirname(project_dir)
    project_name = os.path.basename(project_dir)

    cmd = [
        eclipsec,
        "-nosplash",
        "--launcher.suppressErrors",
        "-application", "org.eclipse.cdt.managedbuilder.core.headlessbuild",
        "-data", workspace_dir,
        "-import", project_dir,
        "-build", f"{project_name}/Debug",
    ]

    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            creationflags=creationflags,
            timeout=300,
        )
        if proc.returncode == 0:
            return True, f"e2 studio 编译成功\n{proc.stdout[-500:]}"
        else:
            return False, f"e2 studio 编译失败 (退出码 {proc.returncode})\n{proc.stderr[-500:]}\n{proc.stdout[-500:]}"
    except subprocess.TimeoutExpired:
        return False, "编译超时 (5分钟)。"
    except Exception as e:
        return False, f"编译出错: {e}"


# --------------- QThread worker ---------------

class ProjectCreateWorker(QThread):
    """Background thread for project creation (file copy can be slow)."""

    progress_update = pyqtSignal(str, int)        # message, percent
    creation_finished = pyqtSignal(bool, str, str)  # success, detail, project_dir

    def __init__(self, template_name: str, workspace_dir: str, project_name: str):
        super().__init__()
        self.template_name = template_name
        self.workspace_dir = workspace_dir
        self.project_name = project_name

    def run(self):
        def _progress(msg: str, pct: int):
            self.progress_update.emit(msg, pct)

        success, detail = create_project(
            self.template_name,
            self.workspace_dir,
            self.project_name,
            progress_callback=_progress,
        )
        project_dir = os.path.join(self.workspace_dir, self.project_name) if success else ""
        self.creation_finished.emit(success, detail, project_dir)
