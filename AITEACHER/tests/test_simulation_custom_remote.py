from collections import deque
from pathlib import Path
import queue
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.live import LiveRuntime
from simulator.panel import validate_payload


class CustomRemoteTests(unittest.TestCase):
    def test_payload_validation(self):
        self.assertEqual(validate_payload('4'), ('4', ''))
        self.assertEqual(validate_payload('AT+RUN'), ('AT+RUN', ''))
        self.assertIsNone(validate_payload('左转')[0])
        self.assertIsNone(validate_payload('')[0])
        self.assertIsNone(validate_payload('A' * 33)[0])

    def test_payload_is_sent_one_character_at_a_time(self):
        runtime = object.__new__(LiveRuntime)
        runtime.inbox = queue.Queue(maxsize=1)
        runtime.pending_input = deque()
        runtime.inbox.put_nowait('AT')
        self.assertEqual(runtime.take_input(), 'A')
        self.assertEqual(runtime.take_input(), 'T')
        self.assertIsNone(runtime.take_input())

    def test_new_press_replaces_unsent_payload(self):
        runtime = object.__new__(LiveRuntime)
        runtime.inbox = queue.Queue(maxsize=1)
        runtime.pending_input = deque('OLD')
        runtime.inbox.put_nowait('N')
        self.assertEqual(runtime.take_input(), 'N')
        self.assertIsNone(runtime.take_input())


if __name__ == '__main__':
    unittest.main()
