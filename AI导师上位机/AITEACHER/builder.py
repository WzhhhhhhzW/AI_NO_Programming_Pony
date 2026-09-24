import glob
import json
import os
import re
import subprocess
import sys
import threading

from PyQt6.QtCore import QThread, pyqtSignal

# 界面上的【一键编译】和 agent 的编译自检共用同一个 Debug 目录，
# 同时跑两个 make 会互相删对方的 .o。谁先拿到锁谁编，另一个直接拒绝。
BUILD_LOCK = threading.Lock()

from config import _CONFIG_DIR
from flasher import app_dir, resource_dirs

BUILD_CONFIG_FILE = os.path.join(_CONFIG_DIR, "build_config.json")


def _e2studio_roots():
    """扫描各盘常见位置，返回可能的 e2 studio 安装根目录列表。"""
    roots = []
    if os.name == "nt":
        for drv in "CDEFG":
            for pat in (rf"{drv}:\Renesas\e2_studio", rf"{drv}:\Renesas\e2studio*",
                        rf"{drv}:\Renesas\RA\e2studio*",
                        rf"{drv}:\*\Renesas\e2_studio", rf"{drv}:\e2_studio"):
                roots.extend(glob.glob(pat))
    return roots


def find_toolchain_bin():
    """返回含 arm-none-eabi-gcc 的 bin 目录。

    优先级：随程序分发的 tools/toolchain > e2 studio 配套安装的
    Arm GNU Toolchain（学生装 e2 studio 时勾选的那份）> 系统 PATH。
    """
    gcc = "arm-none-eabi-gcc.exe" if os.name == "nt" else "arm-none-eabi-gcc"
    for base in resource_dirs():
        bundled = os.path.join(base, "tools", "toolchain", "bin")
        if os.path.exists(os.path.join(bundled, gcc)):
            return bundled

    candidates = []
    if os.name == "nt":
        for root in _e2studio_roots():
            # e2 studio 安装器把工具链装在与 Renesas 同级的目录下
            # 例如 D:\applications\Renesas\e2_studio 与
            #      D:\applications\Arm GNU Toolchain arm-none-eabi\13.2 Rel1
            parent = os.path.dirname(os.path.dirname(root))
            candidates += glob.glob(os.path.join(parent, "Arm GNU Toolchain arm-none-eabi", "*", "bin"))
            # 新 FSP 工具链在 toolchains/<arch>/<version>/bin 下
            candidates += glob.glob(os.path.join(root, "toolchains", "*", "*", "bin"))
        for pf in (r"C:\Program Files (x86)", r"C:\Program Files"):
            candidates += glob.glob(os.path.join(pf, "Arm GNU Toolchain arm-none-eabi", "*", "bin"))
            candidates += glob.glob(os.path.join(pf, "GNU Arm Embedded Toolchain", "*", "bin"))
    for d in sorted(candidates, reverse=True):
        if os.path.exists(os.path.join(d, gcc)):
            return d

    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and os.path.exists(os.path.join(d, gcc)):
            return d
    return ""


def find_make():
    """返回 make 可执行文件路径。需 GNU Make >= 4.0（FSP makefile 用了 $(file)）。

    Windows 上优先用 e2 studio 自带的 gnumake 插件（4.3.1，与 IDE 构建同款）。
    """
    name = "make.exe" if os.name == "nt" else "make"
    for base in resource_dirs():
        bundled = os.path.join(base, "tools", "make", name)
        if os.path.exists(bundled):
            return bundled

    if os.name == "nt":
        for root in _e2studio_roots():
            hits = glob.glob(os.path.join(root, "eclipse", "plugins",
                                          "com.renesas.ide.exttools.gnumake*", "mk", "make.exe"))
            if hits:
                return sorted(hits)[-1]

    # 非 Windows 优先 gmake（mac 自带 make 常为 3.81，不支持 $(file)）
    candidates = ["gmake", "make"] if os.name != "nt" else ["make"]
    for c in candidates:
        for d in os.environ.get("PATH", "").split(os.pathsep):
            p = os.path.join(d, c + (".exe" if os.name == "nt" else ""))
            if d and os.path.exists(p):
                return p
    return name


def find_debug_dir(project_dir):
    """在工程目录里定位含 makefile 的构建目录（通常是 Debug/，其次 Release/）。"""
    if not project_dir:
        return ""
    # 用户直接选到了含 makefile 的目录
    if os.path.exists(os.path.join(project_dir, "makefile")) or \
       os.path.exists(os.path.join(project_dir, "Makefile")):
        return project_dir
    for sub in ("Debug", "Release"):
        d = os.path.join(project_dir, sub)
        if os.path.exists(os.path.join(d, "makefile")) or \
           os.path.exists(os.path.join(d, "Makefile")):
            return d
    return ""


def makefile_init_path_dirs(debug_dir):
    """读 Debug/makefile.init 里那行 ``export PATH=...``，只留下本机真实存在的目录。

    e2 studio 生成 makefile.init 时，会把**生成那台机器**的整个 PATH 抄进去
    写死，例如 ``C:\\Renesas\\RA\\e2studio_v2025-04.1...\\toolchains\\gcc_arm\\
    13.2.rel1\\bin``。make 读到这行会直接顶掉我们传进去的 PATH，于是所有
    ``arm-none-eabi-gcc`` 全部 command not found（Linux 上必然，Windows 上
    只要 e2 studio 装的位置或版本不同就会）。

    保留其中仍然存在的目录是有意义的：Windows 上 busybox 的 rm / xargs 就在
    这些目录里，``make clean`` 要用。不存在的一律丢掉。
    """
    init_file = os.path.join(debug_dir, "makefile.init")
    if not os.path.exists(init_file):
        return []
    try:
        with open(init_file, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    dirs = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("export PATH="):
            continue
        for raw in line[len("export PATH="):].split(";"):
            d = raw.strip().rstrip("\\/")
            if d and os.path.isdir(d) and d not in dirs:
                dirs.append(d)
    return dirs


def build_path_value(debug_dir, toolchain_bin, make_path):
    """拼出传给 make 的 PATH：我们指定的工具链优先，其余按可用性兜底。"""
    parts = []
    for d in (toolchain_bin, os.path.dirname(make_path) if make_path else ""):
        if d and os.path.isdir(d) and d not in parts:
            parts.append(d)
    for d in makefile_init_path_dirs(debug_dir):
        if d not in parts:
            parts.append(d)
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and d not in parts:
            parts.append(d)
    return os.pathsep.join(parts)


_DIAG_RE = re.compile(
    r"^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?:(?P<col>\d+):)?\s*"
    r"(?P<kind>error|fatal error|warning):\s*(?P<msg>.*)$"
)


def parse_diagnostics(lines, debug_dir, project_root=""):
    """从 make 的输出里挑出编译器诊断。

    界面上的问题列表和 agent 的编译自检共用这一份，省得两边的解析结果对不上。
    编译器报的路径是相对 Debug/ 的（``../src/Face.c``），这里换算成绝对路径
    和相对工程根的短路径。
    """
    out = []
    seen = set()
    for line in lines:
        m = _DIAG_RE.match(line.strip())
        if not m:
            continue
        full = os.path.normpath(os.path.join(debug_dir, m.group("file")))
        try:
            rel = os.path.relpath(full, project_root) if project_root else m.group("file")
        except ValueError:
            rel = m.group("file")
        item = {
            "file": rel.replace("\\", "/"),
            "abs_path": full,
            "line": int(m.group("line")),
            "kind": "warning" if m.group("kind") == "warning" else "error",
            "message": m.group("msg").strip(),
        }
        key = (item["abs_path"], item["line"], item["message"])
        if key in seen:          # -j4 下同一条会被重复打印
            continue
        seen.add(key)
        out.append(item)
    # 错误排前面，学生一眼看到要修的
    out.sort(key=lambda d: (d["kind"] == "warning", d["file"], d["line"]))
    return out


FIRMWARE_PATTERNS = ("*.srec", "*.hex", "*.mot")


def detect_firmware(debug_dir):
    """在构建目录里找固件，优先 .srec（RA/FSP 默认），其次 .hex / .mot。"""
    if not debug_dir:
        return ""
    for ext in FIRMWARE_PATTERNS:
        hits = sorted(glob.glob(os.path.join(debug_dir, ext)),
                      key=os.path.getmtime, reverse=True)
        if hits:
            return hits[0]
    return ""


def purge_firmware(debug_dir):
    """构建前删掉旧固件。

    这是"产出必然是本次构建的"唯一可靠保证——不能指望 ``make clean``：
    FSP 生成的 makefile 里 clean 目标每条命令都带 ``-`` 前缀（忽略退出码），
    而且用了 ``xargs``（Windows 上未必存在），失败也是静默的。

    返回 (删除的文件列表, 删不掉的文件列表)。删不掉通常是被 RFP 或
    资源管理器占着，这种情况必须报错，否则又会把旧固件当成新的。
    """
    removed, failed = [], []
    for ext in FIRMWARE_PATTERNS:
        for path in glob.glob(os.path.join(debug_dir, ext)):
            try:
                os.remove(path)
                removed.append(os.path.basename(path))
            except OSError:
                failed.append(os.path.basename(path))
    return removed, failed


def load_build_config():
    # 只存环境差异（工具链在哪、make 在哪）。工程路径由界面的
    # "当前工程"决定，不在这里存第二份。
    cfg = {"toolchain_bin": "", "make_path": ""}
    if os.path.exists(BUILD_CONFIG_FILE):
        try:
            with open(BUILD_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in cfg:
                if data.get(key):
                    cfg[key] = data[key]
        except Exception:
            pass
    # 校验持久化的路径仍然存在（打包 exe 的临时解压目录每次启动会变）
    if cfg["toolchain_bin"] and not os.path.isdir(cfg["toolchain_bin"]):
        cfg["toolchain_bin"] = ""
    if cfg["make_path"] and os.path.sep in cfg["make_path"] and not os.path.exists(cfg["make_path"]):
        cfg["make_path"] = ""
    if not cfg["toolchain_bin"]:
        cfg["toolchain_bin"] = find_toolchain_bin()
    if not cfg["make_path"]:
        cfg["make_path"] = find_make()
    return cfg


def save_build_config(cfg):
    try:
        with open(BUILD_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


class BuildWorker(QThread):
    output_line = pyqtSignal(str)
    build_finished = pyqtSignal(bool, str, str)  # success, message, firmware_path

    def __init__(self, debug_dir, make_path, toolchain_bin, full_rebuild=False):
        super().__init__()
        self.debug_dir = debug_dir
        self.make_path = make_path
        self.toolchain_bin = toolchain_bin
        self.full_rebuild = full_rebuild
        self.build_path = ""
        self.raw_lines = []      # 原始输出，编译完了拿去解析问题列表

    def _run(self, args, env, creationflags, stream=True):
        """跑一条 make 命令，输出逐行发给 UI，返回退出码。

        ``PATH=...`` 走命令行传：make 的命令行变量优先级高于 makefile 里的
        赋值，能盖掉 makefile.init 里那行写死的 ``export PATH=``。
        （只改环境变量没用——那行赋值会把环境里的值覆盖掉。）
        """
        proc = subprocess.Popen(
            [self.make_path, f"PATH={self.build_path}", *args],
            cwd=self.debug_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            env=env,
            creationflags=creationflags,
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                self.raw_lines.append(line)
                if stream:
                    self.output_line.emit(line)
        return proc.wait()

    def diagnostics(self, project_root=""):
        """这次编译解析出来的问题列表，给输出面板用。"""
        return parse_diagnostics(self.raw_lines, self.debug_dir, project_root)

    def run(self):
        if not BUILD_LOCK.acquire(blocking=False):
            self.build_finished.emit(False, "AI 正在编译自检，稍等几秒再点。", "")
            return
        try:
            self.build_path = build_path_value(
                self.debug_dir, self.toolchain_bin, self.make_path)
            env = os.environ.copy()
            env["PATH"] = self.build_path
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

            # 1. 自己删掉旧固件。不依赖 make clean —— 它的每条命令都带 `-`
            #    前缀，失败也返回 0，检查退出码没有意义。
            removed, failed = purge_firmware(self.debug_dir)
            if failed:
                self.build_finished.emit(
                    False,
                    "旧固件删不掉（可能正被烧录工具或资源管理器占用）："
                    + "、".join(failed) + "\n请关闭占用程序后重试。",
                    "",
                )
                return
            if removed:
                self.output_line.emit(f"已清除旧固件: {'、'.join(removed)}")
            self.output_line.emit(f"工具链: {self.toolchain_bin or '(跟随系统 PATH)'}")

            # 2. 可选的彻底重编。默认走增量：只改了 src/*.c 时约 2-3 秒，
            #    全量重编约 20 秒（本工程 29 个编译单元）。
            if self.full_rebuild:
                self.output_line.emit("正在执行 make clean ...")
                self._run(["clean"], env, creationflags)

            # 3. 构建。all 是 makefile 里第一个目标，写出来只是更明确。
            code = self._run(["-j4", "all"], env, creationflags)
            if code != 0:
                self.build_finished.emit(False, f"编译失败 (退出码 {code})", "")
                return

            # 4. 固件是第 1 步删干净之后生成的，存在即本次产出，无需再比对
            fw = detect_firmware(self.debug_dir)
            if not fw:
                self.build_finished.emit(
                    False,
                    "编译退出码为 0，但没有生成任何固件（.srec/.hex/.mot）。\n"
                    "请检查上方日志，或勾选「彻底重编」后重试。",
                    "",
                )
                return
            self.build_finished.emit(True, "编译成功", fw)

        except FileNotFoundError:
            self.build_finished.emit(False, "找不到 make，请检查编译设置中的路径", "")
        except Exception as e:
            self.build_finished.emit(False, f"编译出错: {e}", "")
        finally:
            BUILD_LOCK.release()


def build_firmware_with_eclipsec(project_dir: str) -> tuple[bool, str, str]:
    """Build a Renesas RA project using e2 studio headless (eclipsec/e2studioc).

    Falls back gracefully if e2 studio is not installed — caller should
    use the standard make-based BuildWorker instead.

    Returns (success, message, firmware_path_or_empty_string).
    """
    try:
        from project_manager import build_with_eclipsec
        success, msg = build_with_eclipsec(project_dir)
        if success:
            # Find firmware in Debug/
            debug_dir = find_debug_dir(project_dir)
            fw = detect_firmware(debug_dir) if debug_dir else ""
            return True, msg, fw
        return False, msg, ""
    except ImportError:
        return False, "project_manager 模块不可用，无法使用 e2 studio 编译。", ""
    except Exception as e:
        return False, f"e2 studio 编译异常: {e}", ""
