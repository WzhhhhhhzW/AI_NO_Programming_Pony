"""Port display and command regressions; no hardware access or flashing."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton

import flasher
from dialogs import FlashDialog


class FakePortInfo:
    def __init__(self, port, description="", manufacturer=""):
        self.port = port
        self.device_description = description
        self.device_manufacturer = manufacturer

    def portName(self):
        return self.port

    def systemLocation(self):
        return f"/dev/{self.port}"

    def description(self):
        return self.device_description

    def manufacturer(self):
        return self.device_manufacturer


class SerialPortEnumerationTests(unittest.TestCase):
    def test_natural_com_sort_names_and_raw_compatibility(self):
        infos = [FakePortInfo("COM10", "蓝牙串行端口 (COM10)"),
                 FakePortInfo("COM2", "USB-SERIAL CH340 (COM2)"),
                 FakePortInfo("COM7", "  ", "FTDI")]
        with patch("flasher.os", SimpleNamespace(name="nt")), \
                patch.object(flasher.QSerialPortInfo, "availablePorts", return_value=infos):
            self.assertEqual(flasher.list_serial_port_devices(), [
                {"port": "COM2", "description": "USB-SERIAL CH340"},
                {"port": "COM7", "description": "FTDI"},
                {"port": "COM10", "description": "蓝牙串行端口"},
            ])
            self.assertEqual(flasher.list_serial_ports(), ["COM2", "COM7", "COM10"])

    def test_unix_retains_actual_device_path(self):
        with patch("flasher.os", SimpleNamespace(name="posix")), \
                patch.object(flasher.QSerialPortInfo, "availablePorts",
                             return_value=[FakePortInfo("ttyUSB0", "USB UART")]):
            self.assertEqual(flasher.list_serial_port_devices(), [
                {"port": "/dev/ttyUSB0", "description": "USB UART"}])

    def test_empty_devices_do_not_invent_com_ports(self):
        def missing_registry(*args):
            raise FileNotFoundError("No serial registry")

        registry = SimpleNamespace(HKEY_LOCAL_MACHINE=0, OpenKey=missing_registry)
        with patch("flasher.os", SimpleNamespace(name="nt")), \
                patch.dict("sys.modules", {"winreg": registry}), \
                patch.object(flasher.QSerialPortInfo, "availablePorts", return_value=[]):
            self.assertEqual(flasher.list_serial_port_devices(), [])
            self.assertEqual(flasher.list_serial_ports(), [])

    def test_enumeration_failure_uses_only_known_ports(self):
        with patch.object(flasher.QSerialPortInfo, "availablePorts", side_effect=RuntimeError), \
                patch("flasher._fallback_serial_ports", return_value=["COM12", "COM3"]):
            self.assertEqual(flasher.list_serial_port_devices(), [
                {"port": "COM3", "description": "串口设备（名称未知）"},
                {"port": "COM12", "description": "串口设备（名称未知）"},
            ])


class FlashPortDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["flash-port-tests"])

    def setUp(self):
        self.devices = [
            {"port": "COM2", "description": "USB-SERIAL CH340"},
            {"port": "COM7", "description": "USB Serial Port"},
        ]
        self.port_patch = patch("dialogs.list_serial_port_devices", side_effect=lambda: self.devices)
        self.port_patch.start()
        self.addCleanup(self.port_patch.stop)
        self.dialog = FlashDialog({"port": "COM7"})
        self.addCleanup(self.dialog.close)
        self.addCleanup(self.dialog.deleteLater)

    def refresh(self):
        button = next(button for button in self.dialog.findChildren(QPushButton)
                      if button.text() == "刷新")
        button.click()

    def test_friendly_name_display_and_raw_flash_command(self):
        self.assertEqual(self.dialog.combo_port.currentText(), "COM7 — USB Serial Port")
        self.assertEqual(self.dialog.get_values()["port"], "COM7")
        self.dialog.combo_port.setCurrentIndex(0)
        port = self.dialog.get_values()["port"]
        self.assertEqual(port, "COM2")
        with patch("flasher.os", SimpleNamespace(name="nt")):
            command = flasher.build_flash_command(flasher.DEFAULT_COMMAND_TEMPLATE,
                                                 "rfp-cli.exe", port, "firmware.srec")
        self.assertIn("-port COM2 ", command)
        self.assertNotIn("CH340", command)

    def test_refresh_preserves_raw_selection_and_updates_device_name(self):
        self.devices = [
            {"port": "COM7", "description": "New connected device"},
            {"port": "COM12", "description": "USB UART"},
        ]
        self.refresh()
        self.assertEqual(self.dialog.combo_port.currentIndex(), 0)
        self.assertEqual(self.dialog.combo_port.currentText(), "COM7 — New connected device")
        self.assertEqual(self.dialog.get_values()["port"], "COM7")

    def test_manual_edit_ignores_stale_item_data_and_survives_refresh(self):
        self.dialog.combo_port.setEditText(" COM88 ")
        self.assertEqual(self.dialog.get_values()["port"], "COM88")
        self.refresh()
        self.assertEqual(self.dialog.combo_port.currentText(), "COM88")
        self.assertEqual(self.dialog.get_values()["port"], "COM88")
        self.dialog.combo_port.clearEditText()
        self.assertEqual(self.dialog.get_values()["port"], "")

    def test_disconnected_selection_stays_raw_after_refresh(self):
        self.devices = []
        self.refresh()
        self.assertEqual(self.dialog.combo_port.count(), 0)
        self.assertEqual(self.dialog.combo_port.currentText(), "COM7")
        self.assertEqual(self.dialog.get_values()["port"], "COM7")

    def test_saved_missing_port_and_empty_device_list_are_editable(self):
        self.devices = []
        missing = FlashDialog({"port": "COM24"})
        try:
            self.assertEqual(missing.get_values()["port"], "COM24")
            missing.combo_port.setEditText("COM42")
            self.assertEqual(missing.get_values()["port"], "COM42")
        finally:
            missing.close()
            missing.deleteLater()
        empty = FlashDialog({})
        try:
            self.assertEqual(empty.combo_port.count(), 0)
            self.assertEqual(empty.get_values()["port"], "")
        finally:
            empty.close()
            empty.deleteLater()


if __name__ == "__main__":
    unittest.main()
