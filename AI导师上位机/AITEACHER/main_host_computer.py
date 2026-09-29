import sys

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
    app = QApplication(sys.argv)
    window = CoderUI()
    window.show()
    sys.exit(app.exec())
