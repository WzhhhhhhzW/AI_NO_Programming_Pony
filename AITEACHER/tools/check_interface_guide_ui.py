"""Render and verify the redesigned interface guide in both themes."""
import os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication
from interface_guide import InterfaceGuide, CHAPTERS


app = QApplication(['guide-ui-check'])
QFontDatabase.addApplicationFont('C:/Windows/Fonts/msyh.ttc')
guide = InterfaceGuide()
guide.resize(1180, 820)
guide.show()
app.processEvents()

assert guide.contents.count() == len(CHAPTERS) == 16
assert guide.chapter_title.text() == CHAPTERS[0][0]
guide.search.setText('蓝牙')
app.processEvents()
assert 0 < guide.contents.count() < len(CHAPTERS)
guide.search.clear()
guide.category.setCurrentText('仿真与工具')
app.processEvents()
assert guide.contents.count() == 4
guide.category.setCurrentIndex(0)

output = Path('build')
output.mkdir(exist_ok=True)
guide.apply_theme('light')
app.processEvents()
assert guide.grab().save(str((output / 'interface_guide_light.png').resolve()))
guide.apply_theme('dark')
app.processEvents()
assert guide.grab().save(str((output / 'interface_guide_dark.png').resolve()))
guide.close()
print('PASS: guide layout, search, category filters, light and dark themes.')
