"""从真实主窗口点击知识详解；服务用慢响应替身，不联网、不读取用户配置。"""

import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest

_config = tempfile.TemporaryDirectory(prefix="horse-concept-test-", ignore_cleanup_errors=True)
os.environ["APPDATA"] = _config.name
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import Qt, QCoreApplication, QEvent
from PyQt6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
from ui_main import CoderUI


class SlowCompletions:
    def __init__(self):
        self.calls = []
        self.fail = False
        self.resume = threading.Event()
        self.resume.set()

    def create(self, **kwargs):
        self.calls.append(kwargs)
        time.sleep(0.1)
        if self.fail:
            raise RuntimeError("模拟网络错误")
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="**模拟讲解**"))])
        self.resume.wait(timeout=4)
        time.sleep(0.3)
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="：内容已完成。"))])


class ConceptUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # WebEngine 要求 argv 中有程序名，不能使用 QApplication([])。
        cls.app = QApplication.instance() or QApplication(["concept-ui-test"])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.window = CoderUI()
        self.window.user_endpoint_id = "test-model"
        self.service = SlowCompletions()
        self.window.client = SimpleNamespace(chat=SimpleNamespace(completions=self.service))
        self.window._apply_client_state()
        self.window.show()
        self.app.processEvents()

    def wait_until(self, predicate, timeout=5):
        deadline = time.monotonic() + timeout
        while not predicate():
            self.app.processEvents()
            if time.monotonic() >= deadline:
                self.fail("等待 Qt 回调超时")
            time.sleep(0.005)

    def close_card(self):
        self.window._concept_dialog.close()
        self.app.processEvents()
        self.assertIsNone(self.window._concept_dialog)

    def click_card(self):
        self.assertTrue(self.window.btn_explain.isEnabled())
        self.window.btn_explain.click()
        self.app.processEvents()
        self.assertIsNotNone(self.window._concept_dialog)
        self.assertTrue(self.window._concept_dialog.isVisible())

    def tearDown(self):
        self.service.resume.set()
        self.wait_until(lambda: not self.window._concept_pending)
        if self.window._concept_dialog is not None:
            self.close_card()
        self.window.close()
        self.window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_fresh_launch_opens_local_card_without_ai_reply(self):
        self.assertFalse(self.window.last_ai_response)
        self.assertFalse(self.window.project_root)
        self.click_card()
        self.assertIn("主控芯片", self.window._concept_dialog.text_edit.toPlainText())
        self.assertEqual(self.service.calls, [])

    def test_current_lesson_opens_before_reply_and_uses_current_context(self):
        self.window.difficulty_combo.setCurrentIndex(1)
        self.service.resume.clear()
        self.assertFalse(self.window.last_ai_response)
        self.click_card()
        self.assertTrue(self.window._concept_pending)
        self.wait_until(lambda: "模拟讲解" in self.window._concept_dialog.text_edit.toPlainText())
        self.assertTrue(self.window._concept_pending)
        self.service.resume.set()
        self.wait_until(lambda: not self.window._concept_pending)
        self.assertIn(self.window.lessons.title, next(m["content"] for m in self.service.calls[0]["messages"] if m["role"] == "user"))
        self.close_card()
        self.click_card()
        self.assertEqual(len(self.service.calls), 1)
        self.close_card()
        self.window.go_next_lesson()
        self.click_card()
        self.wait_until(lambda: not self.window._concept_pending)
        self.assertEqual(len(self.service.calls), 2)
        self.assertIn(self.window.lessons.title, next(m["content"] for m in self.service.calls[1]["messages"] if m["role"] == "user"))

    def test_card_can_reopen_while_generating_without_second_request(self):
        self.window.difficulty_combo.setCurrentIndex(1)
        self.click_card()
        worker = self.window.worker_explain
        self.close_card()
        self.click_card()
        self.assertIs(worker, self.window.worker_explain)
        self.wait_until(lambda: not self.window._concept_pending)
        self.assertEqual(len(self.service.calls), 1)
        self.assertIn("内容已完成", self.window._concept_dialog.text_edit.toPlainText())

    def test_unavailable_client_opens_explanation_instead_of_returning_silently(self):
        self.window.difficulty_combo.setCurrentIndex(1)
        self.window.client = None
        self.click_card()
        self.assertIn("API 设置", self.window._concept_dialog.text_edit.toPlainText())
        self.assertFalse(self.window._concept_pending)

    def test_network_failure_is_visible_and_can_retry(self):
        self.window.difficulty_combo.setCurrentIndex(1)
        self.service.fail = True
        self.click_card()
        self.wait_until(lambda: not self.window._concept_pending)
        self.assertIn("模拟网络错误", self.window._concept_dialog.text_edit.toPlainText())
        self.close_card()
        self.service.fail = False
        self.click_card()
        self.wait_until(lambda: not self.window._concept_pending)
        self.assertIn("内容已完成", self.window._concept_dialog.text_edit.toPlainText())


if __name__ == "__main__":
    unittest.main()
