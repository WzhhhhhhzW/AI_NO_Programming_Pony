"""
Environment detection for Renesas development tools.
Finds e2 studio, RA Smart Configurator (RASC), ARM toolchain, and GNU Make.

Used by project_manager.py and builder.py to locate the tools needed
for project creation, code generation, compilation, and flashing.
"""
import glob
import os
import sys
from typing import Optional, Tuple


# --------------- caching ---------------

_cache: dict = {}


def _cached(key: str, factory):
    """Memoize tool lookups so filesystem is scanned only once per key."""
    if key not in _cache:
        _cache[key] = factory()
    return _cache[key]


# --------------- path helpers ---------------

def app_dir() -> str:
    """Directory containing the running application.

    When frozen (PyInstaller) this is the directory holding the exe.
    In dev mode it is the directory of this source file.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# --------------- e2 studio ---------------

def _find_e2studio_impl() -> Optional[str]:
    """Return path to e2studio executable (GUI), or None."""
    if os.name != "nt":
        return None

    # Common installation roots (glob versioned directories)
    patterns = [
        r"C:\Renesas\RA\e2studio*",
        r"D:\Renesas\RA\e2studio*",
        r"C:\Renesas\e2_studio*",
        r"D:\Renesas\e2_studio*",
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        for root in hits:
            exe = os.path.join(root, "eclipse", "e2studio.exe")
            if os.path.exists(exe):
                return exe
    return None


def find_e2studio() -> Optional[str]:
    """Path to e2studio.exe (GUI), or None if not installed."""
    return _cached("e2studio", _find_e2studio_impl)


def _find_e2studioc_impl() -> Optional[str]:
    """Return path to e2studioc.exe (console / headless), or None."""
    gui = find_e2studio()
    if gui:
        c_exe = os.path.join(os.path.dirname(gui), "e2studioc.exe")
        if os.path.exists(c_exe):
            return c_exe
    return None


def find_e2studioc() -> Optional[str]:
    """Path to e2studioc.exe (console variant for headless builds), or None."""
    return _cached("e2studioc", _find_e2studioc_impl)


def find_e2studio_root() -> Optional[str]:
    """Root directory of the e2 studio installation.

    E.g. ``C:\\Renesas\\RA\\e2studio_v2025-04.1_fsp_v6.0.0``.
    """
    gui = find_e2studio()
    if gui:
        # gui is <root>/eclipse/e2studio.exe
        return os.path.dirname(os.path.dirname(gui))
    return None


# --------------- RA Smart Configurator (RASC) ---------------

def _find_rasc_impl() -> Optional[str]:
    """Return path to rasc.exe, or None.

    RASC may be bundled inside e2 studio (as an Eclipse plugin) OR
    installed as a standalone tool.  The standalone form is preferred
    because it can be launched independently.

    Standalone paths:
      C:\\Renesas\\RA\\sc_v*\\eclipse\\rasc.exe

    Bundled inside e2 studio (FSP ≥ 6.x):
      The RASC functionality is accessed via e2studio's plugin system,
      NOT as a separate rasc.exe.  In that case we return None and
      callers fall back to e2studio.exe with appropriate arguments.
    """
    if os.name != "nt":
        return None

    # Standalone RASC
    for base in (r"C:\Renesas\RA", r"D:\Renesas\RA"):
        pattern = os.path.join(base, "sc_v*", "eclipse", "rasc.exe")
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]  # newest version

    return None


def find_rasc() -> Optional[str]:
    """Path to standalone rasc.exe, or None if not installed."""
    return _cached("rasc", _find_rasc_impl)


def find_rasc_or_e2studio() -> Optional[str]:
    """Best available RASC-like launcher.

    Returns rasc.exe if standalone, otherwise e2studio.exe (which
    has RASC integrated as a plugin for FSP ≥ 6.x).
    """
    rasc = find_rasc()
    if rasc:
        return rasc
    return find_e2studio()


# --------------- toolchain ---------------

def _find_toolchain_bin_impl() -> Optional[str]:
    """Return path to the directory containing arm-none-eabi-gcc(.exe)."""
    gcc = "arm-none-eabi-gcc.exe" if os.name == "nt" else "arm-none-eabi-gcc"

    # 1. Bundled with the app
    bundled = os.path.join(app_dir(), "tools", "toolchain", "bin")
    if os.path.exists(os.path.join(bundled, gcc)):
        return bundled

    # 2. Inside e2 studio installation
    root = find_e2studio_root()
    if root:
        tc_dir = os.path.join(root, "toolchains")
        if os.path.isdir(tc_dir):
            # e.g. toolchains/gcc_arm/13.2.rel1/bin/
            for entry in os.listdir(tc_dir):
                gcc_dir = os.path.join(tc_dir, entry)
                if not os.path.isdir(gcc_dir):
                    continue
                # Some versions have version subdirectories
                for item in os.listdir(gcc_dir):
                    candidate = os.path.join(gcc_dir, item, "bin")
                    if os.path.exists(os.path.join(candidate, gcc)):
                        return candidate
                # ...others have bin directly
                candidate = os.path.join(gcc_dir, "bin")
                if os.path.exists(os.path.join(candidate, gcc)):
                    return candidate

    # 3. Common standalone toolchain paths
    if os.name == "nt":
        for pf in (r"C:\Program Files (x86)", r"C:\Program Files"):
            for pat in (
                "Arm GNU Toolchain arm-none-eabi",
                "GNU Arm Embedded Toolchain",
                "GCC ARM Embedded",
            ):
                for entry in sorted(glob.glob(os.path.join(pf, pat, "*", "bin")), reverse=True):
                    if os.path.exists(os.path.join(entry, gcc)):
                        return entry
                entry = os.path.join(pf, pat, "bin")
                if os.path.exists(os.path.join(entry, gcc)):
                    return entry

    # 4. PATH fallback
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and os.path.exists(os.path.join(d, gcc)):
            return d

    return None


def find_toolchain_bin() -> Optional[str]:
    """Directory containing arm-none-eabi-gcc, or None."""
    return _cached("toolchain_bin", _find_toolchain_bin_impl)


# --------------- GNU Make ---------------

def _find_make_impl() -> Optional[str]:
    """Return path to GNU Make executable (>= 4.0 required by FSP)."""
    name = "make.exe" if os.name == "nt" else "make"

    # 1. Bundled
    bundled = os.path.join(app_dir(), "tools", "make", name)
    if os.path.exists(bundled):
        return bundled

    # 2. e2 studio gnumake plugin (Windows)
    if os.name == "nt":
        root = find_e2studio_root()
        if root:
            hits = glob.glob(os.path.join(
                root, "eclipse", "plugins",
                "com.renesas.ide.exttools.gnumake*", "mk", "make.exe"))
            if hits:
                return sorted(hits)[-1]

    # 3. PATH fallback
    candidates = ["gmake", "make"] if os.name != "nt" else ["make"]
    for c in candidates:
        exe_name = c + (".exe" if os.name == "nt" else "")
        for d in os.environ.get("PATH", "").split(os.pathsep):
            p = os.path.join(d, exe_name)
            if d and os.path.exists(p):
                return p
    return name


def find_make() -> Optional[str]:
    """Path to GNU Make, or the string 'make'/'make.exe' as fallback."""
    return _cached("make", _find_make_impl)


# --------------- aggregate status ---------------

def get_environment_status() -> dict:
    """Return a summary of what's installed / detected."""
    return {
        "e2studio": find_e2studio(),
        "e2studioc": find_e2studioc(),
        "rasc": find_rasc(),
        "toolchain_bin": find_toolchain_bin(),
        "make": find_make(),
        "e2studio_root": find_e2studio_root(),
    }


def is_toolchain_ready() -> Tuple[bool, str]:
    """Check whether the minimum toolchain (gcc + make) is available."""
    gcc = find_toolchain_bin()
    if not gcc:
        return False, "未找到 arm-none-eabi-gcc 工具链。请安装 e2 studio 并勾选 GNU Arm Embedded 工具链。"
    mk = find_make()
    if not mk:
        return False, "未找到 GNU Make。请安装 e2 studio。"
    return True, "工具链就绪"


def is_e2studio_ready() -> Tuple[bool, str]:
    """Check whether e2 studio (or RASC) is available for project creation."""
    rasc = find_rasc_or_e2studio()
    if not rasc:
        return False, (
            "未检测到 e2 studio 或 RA Smart Configurator。\n"
            "请先安装 e2 studio (含 FSP) 或 RA Smart Configurator。\n"
            "下载地址: https://www.renesas.cn/zh/software-tool/ra-smart-configurator"
        )
    return True, f"已检测到: {rasc}"
