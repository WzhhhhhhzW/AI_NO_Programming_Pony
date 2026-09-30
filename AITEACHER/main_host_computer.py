import sys
from pathlib import Path
from PyQt6.QtGui import QIcon

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

# QtWebEngine 必须在 QApplication 实例化之前完成初始化，否则直接抛
# ImportError: QtWebEngineWidgets must be imported ... before a QCoreApplication
# instance is created。对话区用的就是它（chat_view.py），所以这两行要放在
# 任何界面模块导入之前，不能挪。
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
import PyQt6.QtWebEngineWidgets  # noqa: E402,F401  仅为触发初始化

import logs  # noqa: E402

logs.setup()

from loguru import logger  # noqa: E402
from ui_main import CoderUI  # noqa: E402

if __name__ == "__main__":
    logger.info("启动")
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("RenesasHorseTutor.Desktop")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "app_icon.ico")))
    window = CoderUI()
    window.show()
    if "--simulation" in sys.argv:
        window.open_simulation()
    if "--interface-guide" in sys.argv:
        window.open_interface_guide()
    if "--serial-debug" in sys.argv:
        window.open_serial_debug()
    if "--oled-tool" in sys.argv:
        window.open_oled_tool()
    if "--tutorials" in sys.argv:
        window.open_tutorials()
    sys.exit(app.exec())
