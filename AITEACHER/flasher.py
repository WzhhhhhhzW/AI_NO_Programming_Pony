import glob
import json
import os
import shlex
import subprocess
import sys

from PyQt6.QtCore import QThread, pyqtSignal

from config import _CONFIG_DIR

FLASH_CONFIG_FILE = os.path.join(_CONFIG_DIR, "flash_config.json")

# {rfp} = rfp-cli 路径, {port} = 串口, {hex} = 固件文件
# -a: 擦除+编程+校验, -run: 完成后让芯片复位运行, 详见 tools/rfp-cli/rfp-cli.md
DEFAULT_COMMAND_TEMPLATE = '"{rfp}" -device ra -port {port} -a "{hex}" -run'


def app_dir():
    """随程序分发的资源根目录（tools/ 就挂在它下面）。

    PyInstaller 6.x 的 onedir 模式把数据文件放进 ``<exe 同级>/_internal/``
    而不是 exe 旁边，所以要优先用 ``sys._MEIPASS``——onefile 下它是临时
    解压目录，onedir 下它就是 _internal/，两种都对。
    """
    base = getattr(sys, "_MEIPASS", "")
    if base:
        return base
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_dirs():
    """找自带工具时要看的所有目录。

    除了打包进去的那份，还看 exe 旁边——队友可能事后往那儿丢一个
    toolchain/ 或 make/，不重新打包也能用。
    """
    dirs = [app_dir()]
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if exe_dir not in dirs:
            dirs.append(exe_dir)
    return dirs


def load_flash_config():
    cfg = {"rfp_path": "", "port": "", "hex_path": "", "template": DEFAULT_COMMAND_TEMPLATE}
    if os.path.exists(FLASH_CONFIG_FILE):
        try:
            with open(FLASH_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in cfg:
                if data.get(key):
                    cfg[key] = data[key]
            # 迁移早期版本保存的旧模板
            if cfg["template"] == '"{rfp}" -device ra -tool com -port {port} -a "{hex}"':
                cfg["template"] = DEFAULT_COMMAND_TEMPLATE
        except Exception:
            pass
    # 打包成单文件 exe 时 rfp-cli 解压在临时目录，每次启动路径都变，
    # 上次保存的路径会失效；固件文件也可能被移动/删除——一律校验后再用
    if cfg["rfp_path"] and not os.path.exists(cfg["rfp_path"]):
        cfg["rfp_path"] = ""
    if cfg["hex_path"] and not os.path.exists(cfg["hex_path"]):
        cfg["hex_path"] = ""
    if not cfg["rfp_path"]:
        cfg["rfp_path"] = find_rfp_cli()
    return cfg


def save_flash_config(cfg):
    try:
        with open(FLASH_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def find_rfp_cli():
    # 优先使用随程序分发的 tools/rfp-cli（PyInstaller 打包后解压在 _MEIPASS）
    # mac/Linux 下若放入对应平台的 rfp-cli 原生二进制则优先选用
    search_dirs = [os.path.join(d, "tools", "rfp-cli") for d in resource_dirs()]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        search_dirs.append(os.path.join(sys._MEIPASS, "tools", "rfp-cli"))
    names = ["rfp-cli.exe"] if os.name == "nt" else ["rfp-cli", "rfp-cli.exe"]
    for d in search_dirs:
        for name in names:
            path = os.path.join(d, name)
            if os.path.exists(path):
                return path

    if os.name == "nt":
        patterns = [
            r"C:\Program Files (x86)\Renesas Electronics\Programming Tools\Renesas Flash Programmer*\rfp-cli.exe",
            r"C:\Program Files\Renesas Electronics\Programming Tools\Renesas Flash Programmer*\rfp-cli.exe",
        ]
        for pattern in patterns:
            hits = sorted(glob.glob(pattern))
            if hits:
                return hits[-1]
    return ""


def list_serial_ports():
    ports = []
    if os.name == "nt":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM")
            i = 0
            while True:
                try:
                    ports.append(winreg.EnumValue(key, i)[1])
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except OSError:
            pass
        if not ports:
            ports = [f"COM{n}" for n in range(1, 10)]
    else:
        ports = sorted(glob.glob("/dev/cu.*") + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    return ports


def build_flash_command(template, rfp_path, port, hex_path):
    cmd_str = template.format(rfp=rfp_path, port=port, hex=hex_path)
    if os.name == "nt":
        # Windows 的 CreateProcess 接受整条命令字符串, 保留原样以免路径中的反斜杠被转义
        return cmd_str
    return shlex.split(cmd_str)


class FlashWorker(QThread):
    output_line = pyqtSignal(str)
    flash_finished = pyqtSignal(bool, str)

    def __init__(self, command):
        super().__init__()
        self.command = command

    def run(self):
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                errors="replace",
                creationflags=creationflags,
            )
            lines = []
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    lines.append(line)
                    self.output_line.emit(line)
            code = proc.wait()
            # 不只信退出码：输出里出现 [Error]、或完全无输出，都按失败处理
            has_error = any("[error]" in l.lower() for l in lines)
            if code == 0 and lines and not has_error:
                self.flash_finished.emit(True, "烧录完成")
            elif has_error:
                self.flash_finished.emit(False, "烧录失败（rfp-cli 报告了错误，见上方输出）")
            elif not lines:
                self.flash_finished.emit(False, "烧录异常：rfp-cli 没有任何输出，请检查路径与参数")
            else:
                self.flash_finished.emit(False, f"烧录失败 (退出码 {code})")
        except FileNotFoundError:
            self.flash_finished.emit(False, "找不到 rfp-cli，请检查烧录设置中的路径")
        except Exception as e:
            self.flash_finished.emit(False, f"烧录出错: {e}")
