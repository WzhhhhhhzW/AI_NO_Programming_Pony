"""检查发行目录中的 Qt 原生模块，避免源码环境掩盖缺失或冲突的 DLL。"""

import argparse
import importlib
import os
from pathlib import Path
import sys
import types


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="包含 exe 和 _internal 的目录")
    args = parser.parse_args()
    internal = args.bundle.resolve() / "_internal"
    qt_package = internal / "PyQt6"
    qt_bin = qt_package / "Qt6" / "bin"
    if not (qt_package / "QtCore.pyd").is_file():
        raise SystemExit(f"缺少打包的 QtCore.pyd：{qt_package}")

    # PyQt6 的 __init__ 在 exe 的 PYZ 中。显式指定包路径，不能退回
    # 当前虚拟环境里的 PyQt6（那样会把有问题的发行包误判为正常）。
    package = types.ModuleType("PyQt6")
    package.__path__ = [str(qt_package)]
    package.__file__ = str(qt_package / "__init__.py")
    sys.modules["PyQt6"] = package
    handles = [os.add_dll_directory(str(internal)),
               os.add_dll_directory(str(qt_bin))]
    try:
        for name in ("QtCore", "QtSerialPort", "QtGui", "QtWidgets", "QtWebEngineCore",
                     "QtWebEngineWidgets", "QtPdf", "QtPdfWidgets", "QtMultimedia", "QtMultimediaWidgets", "Qsci"):
            module = importlib.import_module(f"PyQt6.{name}")
            if Path(module.__file__).resolve().parent != qt_package:
                raise RuntimeError(f"加载了发行目录以外的模块：{module.__file__}")
            print(f"OK: packaged PyQt6.{name}")
    finally:
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
