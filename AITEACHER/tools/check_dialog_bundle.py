"""Verify rendering and mouse behavior from compiled release dialogs."""
import os
import sys
import types
import json
import argparse
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--bundle', type=Path, default=root / 'dist' / 'RenesasHorseTutor')
parser.add_argument('--output', type=Path, default=root / 'build' / 'v16_20_validation')
args = parser.parse_args()
bundle = args.bundle.resolve()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=True)
internal = bundle / '_internal'
qt_package = internal / 'PyQt6'
qt_bin = qt_package / 'Qt6' / 'bin'
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['QT_PLUGIN_PATH'] = str(qt_package / 'Qt6' / 'plugins')
dll_handles = [os.add_dll_directory(str(internal)), os.add_dll_directory(str(qt_bin))]
package = types.ModuleType('PyQt6')
package.__path__ = [str(qt_package)]
package.__file__ = str(qt_package / '__init__.py')
sys.modules['PyQt6'] = package
sys._MEIPASS = str(internal)
# The compiled config module creates its settings directory on import. Isolate
# that side effect in the validation output instead of using personal settings.
os.environ['APPDATA'] = str(out / 'appdata')

archive = CArchiveReader(str(bundle / 'RenesasHorseTutor.exe')).open_embedded_archive('PYZ.pyz')
compiled_modules = ('config', 'environment', 'styles', 'project_manager',
                    'flasher', 'dialogs', 'interface_guide', 'oled_tool', 'tutorials')
for name in compiled_modules:
    module = types.ModuleType(name)
    module.__file__ = str(internal / f'{name}.py')
    sys.modules[name] = module
    exec(archive.extract(name), module.__dict__)

from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QCoreApplication, QEvent
from PyQt6.QtGui import QMouseEvent, QImage, QFontDatabase, QFont, QPixmap, QPainter
from PyQt6.QtWidgets import (QApplication, QPushButton, QStyle, QStyleOptionSpinBox,
                             QLabel, QWidget)
from PyQt6 import QtCore
from oled_tool import OledToolDialog
from tutorials import TutorialDialog
from interface_guide import InterfaceGuide, CHAPTERS
from dialogs import FlashDialog
import dialogs
from styles import LIGHT_STYLESHEET, MODERN_STYLESHEET

assert Path(QtCore.__file__).resolve().parent == qt_package.resolve()
app = QApplication([])
# Offscreen Qt does not use Windows' font discovery. Use the installed fonts
# for readable verification captures without copying fonts into the release.
for filename in ('msyh.ttc', 'msyhbd.ttc', 'segoeui.ttf', 'consola.ttf'):
    font_path = Path(os.environ['WINDIR']) / 'Fonts' / filename
    if font_path.is_file():
        QFontDatabase.addApplicationFont(str(font_path))
app.setFont(QFont('Microsoft YaHei', 10))
results = []
print('QT_MODULE=' + QtCore.__file__, flush=True)
assert not QImage(str(internal / 'assets' / 'spin_up_dark.png')).isNull()

def settle():
    for _ in range(6):
        app.processEvents()

def click(widget, point=None):
    point = QPointF(point or widget.rect().center())
    for event_type, buttons in ((QEvent.Type.MouseButtonPress, Qt.MouseButton.LeftButton),
                                (QEvent.Type.MouseButtonRelease, Qt.MouseButton.NoButton)):
        event = QMouseEvent(event_type, point, Qt.MouseButton.LeftButton,
                            buttons, Qt.KeyboardModifier.NoModifier)
        QCoreApplication.sendEvent(widget, event)
    settle()

def spin_rect(widget, direction):
    option = QStyleOptionSpinBox()
    widget.initStyleOption(option)
    subcontrol = QStyle.SubControl.SC_SpinBoxUp if direction == 'up' else QStyle.SubControl.SC_SpinBoxDown
    return widget.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, subcontrol, widget)

def verify_spin(widget, label, theme):
    initial = max(widget.minimum() + 1, min(widget.maximum() - 1, widget.value()))
    widget.setValue(initial)
    settle()
    for direction, expected in (('up', initial + 1), ('down', initial)):
        rect = spin_rect(widget, direction)
        assert rect.width() >= 28, (label, rect)
        click(widget, rect.center())
        assert widget.value() == expected, (label, theme, direction, widget.value(), expected)
        results.append(f'{theme}: {label} {direction} OK')
    pixmap = widget.grab()
    image = pixmap.toImage()
    ratio = pixmap.devicePixelRatio()
    for direction in ('up', 'down'):
        center = spin_rect(widget, direction).center()
        contrasting = 0
        for y in range(round((center.y() - 4) * ratio), round((center.y() + 5) * ratio)):
            for x in range(round((center.x() - 6) * ratio), round((center.x() + 7) * ratio)):
                color = image.pixelColor(x, y)
                bright = color.lightness()
                if (theme == 'dark' and bright > 190) or (theme == 'light' and bright < 90):
                    contrasting += 1
        assert contrasting >= 8, (label, theme, direction, 'arrow missing', contrasting)
    return image

def save_widgets(path, *widgets):
    """Capture a dialog and its separate popup window in the same image."""
    captures = []
    bounds = QRect()
    for widget in widgets:
        assert widget.isVisible(), (widget.objectName(), 'capture not visible')
        rect = QRect(widget.mapToGlobal(QPoint(0, 0)), widget.size())
        bounds = bounds.united(rect)
        captures.append((rect, widget.grab()))
    image = QPixmap(bounds.size())
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    for rect, capture in captures:
        painter.drawPixmap(rect.topLeft() - bounds.topLeft(), capture)
    painter.end()
    assert image.save(str(path)), path


for theme in ('dark', 'light'):
    app.setStyleSheet(MODERN_STYLESHEET if theme == 'dark' else LIGHT_STYLESHEET)
    oled = OledToolDialog()
    oled.apply_theme(theme)
    oled.mode.setCurrentIndex(1)
    oled.height_value.setValue(32)
    oled.show()
    settle()
    for label, widget in (('width', oled.width_value), ('height', oled.height_value),
                          ('font_size', oled.font_size), ('threshold', oled.threshold),
                          ('position_x', oled.x), ('position_y', oled.y)):
        verify_spin(widget, label, theme)
    oled.x.setValue(0)
    oled.y.setValue(0)
    oled.height_value.setValue(32)
    clear = next(b for b in oled.findChildren(QPushButton) if b.text() == '清空点阵')
    reset = next(b for b in oled.findChildren(QPushButton) if b.text() == '从来源重新生成')
    click(clear)
    assert not any(any(row) for row in oled.canvas.pixels)
    click(reset)
    assert any(any(row) for row in oled.canvas.pixels)
    results.append(f'{theme}: OLED clear/reset OK')
    oled.grab().save(str(out / f'oled_{theme}.png'))
    up = spin_rect(oled.width_value, 'up')
    down = spin_rect(oled.width_value, 'down')
    oled.width_value.grab(up.united(down)).save(str(out / f'arrows_{theme}.png'))
    oled.close()

    tutorial = TutorialDialog()
    tutorial.apply_theme(theme)
    tutorial.show()
    settle()
    for index, expected in ((0, 25), (1, 72), (2, 5)):
        tutorial.selector.setCurrentIndex(index)
        settle()
        assert tutorial.document.pageCount() == expected
        tutorial.jump(0)
        click(tutorial.next)
        assert tutorial.page.value() == 2
        assert tutorial.view.pageNavigator().currentPage() == 1
        click(tutorial.previous)
        assert tutorial.page.value() == 1
        assert tutorial.view.pageNavigator().currentPage() == 0
        verify_spin(tutorial.page, f'tutorial_{index}_page', theme)
    tutorial.grab().save(str(out / f'tutorial_{theme}.png'))
    results.append(f'{theme}: all three tutorials load and navigate OK')
    tutorial.close()

    guide = InterfaceGuide()
    guide.apply_theme(theme)
    guide.resize(1180, 820)
    guide.show()
    settle()
    assert len(CHAPTERS) == 16
    assert not guide.findChildren(QWidget, 'guideOfflineBadge')
    assert not any('离线可用' in label.text() for label in guide.findChildren(QLabel))
    assert guide.contents.count() == 16
    assert guide.current_chapter == 0
    click(guide.next_button)
    assert guide.current_chapter == 1
    assert guide.chapter_title.text() == CHAPTERS[1][0]
    click(guide.prev_button)
    assert guide.current_chapter == 0
    results.append(f'{theme}: guide badge removed and 16 chapters navigate OK')
    guide.search.setText('API 设置')
    settle()
    assert 4 in guide.matches
    assert guide.contents.count() < 16
    assert guide.contents.count() == len(guide.matches)
    row = guide.matches.index(4)
    guide.contents.setCurrentRow(row)
    settle()
    assert guide.current_chapter == 4
    assert 'base_url' in guide.reader.toPlainText()
    guide.search.clear()
    settle()
    assert guide.contents.count() == 16
    guide.contents.setCurrentRow(0)
    settle()
    guide.grab().save(str(out / f'guide_{theme}.png'))
    results.append(f'{theme}: guide keyword search and clear OK')
    guide.close()

    # Mock discovery only; no serial device is opened and no flashing starts.
    sample_ports = [
        {'port': 'COM3', 'description': 'USB-SERIAL CH340'},
        {'port': 'COM6', 'description': 'Silicon Labs CP210x USB to UART Bridge'},
        {'port': 'COM9', 'description': '蓝牙串行端口 Bluetooth Serial Port'},
    ]
    discovery_calls = []

    def discover_ports():
        discovery_calls.append(True)
        return [dict(port) for port in sample_ports]

    original_discovery = dialogs.list_serial_port_devices
    dialogs.list_serial_port_devices = discover_ports
    parent = QWidget()
    parent.current_theme = theme
    flash = None
    missing_port_dialog = None
    try:
        flash = FlashDialog({'port': 'COM3'}, parent)
        flash.resize(840, 320)
        flash.show()
        settle()
        combo = flash.combo_port
        assert combo.isEditable()
        assert combo.count() == len(sample_ports)
        for index, device in enumerate(sample_ports):
            assert device['port'] in combo.itemText(index)
            assert device['description'] in combo.itemText(index)
            assert combo.itemData(index) == device['port']
        assert flash.get_values()['port'] == 'COM3'
        results.append(f'{theme}: flash friendly device labels and raw COM values OK')

        combo.showPopup()
        settle()
        assert combo.view().isVisible()
        save_widgets(out / f'flash_ports_{theme}.png', flash, combo.view().window())
        combo.view().window().grab().save(str(out / f'flash_port_list_{theme}.png'))
        combo.hidePopup()
        settle()

        combo.setCurrentIndex(combo.findData('COM6'))
        settle()
        assert 'Silicon Labs CP210x' in combo.currentText()
        assert flash.get_values()['port'] == 'COM6'
        results.append(f'{theme}: flash selected friendly entry returns COM6 OK')

        combo.setCurrentIndex(combo.findData('COM3'))
        sample_ports[0]['description'] = 'WCH USB-SERIAL CH340'
        refresh = next(button for button in flash.findChildren(QPushButton)
                       if button.text() == '刷新')
        calls_before = len(discovery_calls)
        click(refresh)
        assert len(discovery_calls) == calls_before + 1
        assert flash.get_values()['port'] == 'COM3'
        assert 'WCH USB-SERIAL CH340' in combo.currentText()
        results.append(f'{theme}: flash refresh updates names and preserves raw selection OK')

        # Editable combo boxes may retain the old item index after typing. A
        # manually entered port must override the stale item's COM value.
        combo.setEditText('COM17')
        settle()
        assert combo.currentText() == 'COM17'
        assert flash.get_values()['port'] == 'COM17'
        click(refresh)
        assert flash.get_values()['port'] == 'COM17'
        results.append(f'{theme}: flash manual port and refresh preservation OK')
        flash.close()

        missing_port_dialog = FlashDialog({'port': 'COM99'}, parent)
        missing_port_dialog.show()
        settle()
        assert missing_port_dialog.get_values()['port'] == 'COM99'
        results.append(f'{theme}: flash saved disconnected port preserved OK')
        missing_port_dialog.close()
    finally:
        dialogs.list_serial_port_devices = original_discovery
        if flash is not None:
            flash.close()
        if missing_port_dialog is not None:
            missing_port_dialog.close()
        parent.close()

report = {'bundle': str(bundle), 'qt_native_module': QtCore.__file__,
          'tested_code': 'compiled modules from RenesasHorseTutor.exe',
          'compiled_modules': list(compiled_modules),
          'checks': results, 'status': 'PASS'}
(out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('BUNDLE_UI_CHECKS=PASS')
print(f'CHECK_COUNT={len(results)}')
print(f'PREVIEWS={out}')
