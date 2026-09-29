import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dog_reference import DogReference, permits_source_explanation, motion_request
from prompts import BEGINNER_AGENT_PROMPT


class DogReferenceTests(unittest.TestCase):
    def test_authorized_origin_only(self):
        self.assertTrue(permits_source_explanation("https://api.deepseek.com/v1/"))
        for url in ("http://api.deepseek.com", "https://api.deepseek.com.example.org", "https://example.com/v1"):
            self.assertFalse(permits_source_explanation(url))

    def test_bundled_files_match_manifest(self):
        bank = DogReference()
        for name, digest in bank.manifest.items():
            self.assertEqual(hashlib.sha256((bank.root / name).read_bytes()).hexdigest(), digest, name)

    def test_requests_select_existing_implementations(self):
        bank = DogReference()
        for request, expected in (("给我 PWM 驱动代码", "src/PWM.c"),
                                  ("让小马前进", "src/action.c"),
                                  ("蓝牙接收指令", "src/hal_entry.c"),
                                  ("OLED 显示文字", "src/oled.c"),
                                  ("显示表情", "src/Face.c"),
                                  ("R_Front_SetDuty 怎么用", "src/PWM.c")):
            with self.subTest(request=request):
                self.assertIn(expected, bank.select(request))
        self.assertIn("Forward_OLD();", bank.read("src/hal_entry.c"))
        self.assertIn("GPT_IO_PIN_GTIOCB", bank.read("src/PWM.c"))

    def test_followup_retains_reference_and_rejects_unknown_path(self):
        bank = DogReference()
        previous = bank.select("PWM")
        self.assertEqual(bank.select("再解释一下", previous), previous)
        with self.assertRaises(ValueError):
            bank.read("../../config.py")

    def test_motion_context_uses_runnable_turn_functions(self):
        context = DogReference().motion_context("帮我实现左转和右转")
        self.assertIn("void Turn_Left()", context)
        self.assertIn("void Turn_Right()", context)
        self.assertIn("L_Front_SetDuty(4);", context)
        self.assertIn("R_Front_SetDuty(5);", context)
        self.assertIn("case Turn_Left_mode:", context)
        self.assertIn("case Turn_Right_mode:", context)
        self.assertTrue(motion_request("修复右转时摔倒"))
        self.assertFalse(motion_request("屏幕显示一行文字"))

    def test_beginner_prompt_requires_reference_and_simulation(self):
        self.assertIn("必须调用 ReadReference", BEGINNER_AGENT_PROMPT)
        self.assertIn("必须调用 ReadSimulation", BEGINNER_AGENT_PROMPT)
        self.assertIn("heading_change_deg", BEGINNER_AGENT_PROMPT)
