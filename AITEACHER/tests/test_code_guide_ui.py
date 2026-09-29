"""真实窗口操作：Dog 原码复制、授权目的地讲解及失败恢复。"""

from test_concept_ui import ConceptUITests
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication
from code_guide import code_blocks
from dog_reference import DogReference


class GuideService:
    def __init__(self, gate):
        self.gate = gate
        self.calls = []
        self.fail = False
        self.prose = False

    def create(self, **kwargs):
        self.calls.append(kwargs)
        time.sleep(0.12)
        if self.fail:
            raise RuntimeError("测试服务不可用")
        first = "PWM 是脉宽调制。" if self.prose else "示例 pwm.c：\n```c\nvoid pwm_init(void) {\n"
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=first))])
        self.gate.wait(timeout=4)
        last = "" if self.prose else "}\n```\npwm.h：\n```c\nvoid pwm_init(void);\n```\n配置 PWM 后调用。"
        yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=last))])


class CodeGuideTests(ConceptUITests):
    # 共用 Qt 环境和知识卡片回归；父类用例也在高级模式的新布局上执行。
    def setUp(self):
        super().setUp()
        self.guide_service = GuideService(self.service.resume)

    def activate_guide(self):
        self.window.client = SimpleNamespace(chat=SimpleNamespace(completions=self.guide_service))
        self.window.user_api_base_url = "https://api.deepseek.com"
        self.window.difficulty_combo.setCurrentIndex(1)
        self.assertTrue(self.window.btn_code_guide.isVisible())
        self.assertIs(self.window.center_stack.currentWidget(), self.window.code_guide)

    def ask(self, question="给我 PWM 驱动代码"):
        self.window.txt_input.setText(question)
        self.window.btn_send.click()

    def tearDown(self):
        self.service.resume.set()
        self.wait_until(lambda: self.window.worker_guide is None)
        super().tearDown()

    def test_original_code_copy_survives_model_response(self):
        self.activate_guide()
        self.window.user_endpoint_id = "test-guide-model"
        self.service.resume.clear()
        with patch("ui_main.APIAdvisor", side_effect=AssertionError("不应启动 agent")):
            self.ask()
            self.wait_until(lambda: "R_GPT_Open" in self.window.code_guide.code.text())
            self.assertIsNotNone(self.window.worker_guide)
            self.assertTrue(self.window.code_guide.copy_button.isEnabled())
            self.assertFalse(self.window.btn_send.isEnabled())
            self.service.resume.set()
            self.wait_until(lambda: self.window.worker_guide is None)
        panel = self.window.code_guide
        self.assertGreater(panel.selector.count(), 2)
        self.assertEqual(panel.selector.currentText(), "Dog/src/PWM.c")
        self.assertTrue(panel.code.isReadOnly())
        panel.copy_button.click()
        self.assertEqual(QApplication.clipboard().text(), DogReference().read("src/PWM.c"))
        panel.selector.setCurrentIndex(1)
        panel.copy_button.click()
        self.assertEqual(QApplication.clipboard().text(), DogReference().read("src/PWM.h"))
        self.assertEqual(self.guide_service.calls[0]["model"], "test-guide-model")
        self.assertTrue(self.guide_service.calls[0]["stream"])
        payload = str(self.guide_service.calls[0]["messages"])
        self.assertIn("Front_Foot_ctrl", payload)
        self.assertIn("Dog/src/PWM.c", payload)
        self.ask("解释刚才的函数")
        self.wait_until(lambda: self.window.worker_guide is None)
        self.assertTrue(any(m["role"] == "assistant" for m in self.guide_service.calls[1]["messages"]))

    def test_file_and_unsaved_edits_preserved_not_uploaded(self):
        self.activate_guide()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.c"
            path.write_text("int private_source_marker = 1;\n", encoding="utf-8")
            self.window.project_root = folder
            self.window.open_file_path(str(path))
            ed = self.window.editor.editor_for(str(path))
            ed.setText("int unsaved_marker = 2;\n")
            ed.setModified(True)
            self.window.btn_code_guide.click()
            self.assertFalse(self.window.btn_save.isEnabled())
            self.ask()
            self.wait_until(lambda: self.window.worker_guide is None)
            self.assertEqual(ed.text(), "int unsaved_marker = 2;\n")
            self.assertTrue(ed.isModified())
            self.assertEqual(path.read_text(encoding="utf-8"), "int private_source_marker = 1;\n")
            payload = str(self.guide_service.calls)
            self.assertNotIn("private_source_marker", payload)
            self.assertNotIn("unsaved_marker", payload)
            self.window.open_file_path(str(path))
            self.assertIs(self.window.center_stack.currentWidget(), self.window.editor)
            self.assertTrue(self.window.btn_save.isEnabled())
            ed.setModified(False)
            self.window.editor.close_all()
            self.window.project_root = ""

    def test_failure_retry_and_prose_keep_original_code(self):
        self.activate_guide()
        self.guide_service.fail = True
        self.ask()
        self.wait_until(lambda: self.window.worker_guide is None)
        self.assertIn("暂不可用", self.window.code_guide.status.text())
        self.assertTrue(self.window.code_guide.copy_button.isEnabled())
        self.assertTrue(self.window.btn_send.isEnabled())
        self.guide_service.fail = False
        self.ask()
        self.wait_until(lambda: self.window.worker_guide is None)
        self.assertTrue(self.window.code_guide.copy_button.isEnabled())
        self.guide_service.prose = True
        self.ask("PWM 是什么？")
        self.wait_until(lambda: self.window.worker_guide is None)
        self.assertEqual(self.window.code_guide.code.text(), DogReference().read("src/PWM.c"))
        self.assertTrue(self.window.code_guide.copy_button.isEnabled())
        self.assertIn("原始文件", self.window.code_guide.status.text())

    def test_other_endpoint_shows_local_source_without_sending(self):
        self.activate_guide()
        self.window.user_api_base_url = "https://example.com/v1"
        self.ask()
        self.assertEqual(self.guide_service.calls, [])
        self.assertIsNone(self.window.worker_guide)
        self.assertEqual(self.window.code_guide.code.text(), DogReference().read("src/PWM.c"))

    def test_mode_switch_retains_guide_and_beginner_route(self):
        self.activate_guide()
        self.ask()
        self.wait_until(lambda: self.window.worker_guide is None)
        code = self.window.code_guide.code.text()
        self.window.difficulty_combo.setCurrentIndex(0)
        self.assertFalse(self.window.btn_code_guide.isVisible())
        self.assertIs(self.window.center_stack.currentWidget(), self.window.editor)
        with patch.object(self.window, "_ask_advisor") as ask_agent:
            self.ask("让小马前进")
            ask_agent.assert_called_once_with("让小马前进")
        self.window.difficulty_combo.setCurrentIndex(1)
        self.assertEqual(self.window.code_guide.code.text(), code)

    def test_parser_handles_partial_fences_and_tilde(self):
        self.assertEqual(code_blocks("```c\nint x;\n``"), [("c", "int x;\n")])
        self.assertEqual(code_blocks("~~~c\nint y;\n~~~"), [("c", "int y;\n")])
