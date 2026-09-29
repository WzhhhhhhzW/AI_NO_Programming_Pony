import queue
import threading
import unittest
from unittest.mock import patch
from pathlib import Path

from simulator.engine import Runtime, load_sources
from simulator.live import LiveRuntime, measure_inputs


class LiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_sources(Path(__file__).resolve().parents[1] / 'reference_projects/Dog')

    def test_integer_mapping_executes_current_driver(self):
        table = measure_inputs(self.sources)
        self.assertEqual(next(s['pulse_ms'] for s in table['R_Front']['samples'] if s['value']==9), 1.8)
        modified = dict(self.sources)
        modified['src/PWM.c'] = modified['src/PWM.c'].replace('(100 - duty)', '(100 - duty - 1)')
        table = measure_inputs(modified)
        self.assertEqual(next(s['pulse_ms'] for s in table['R_Front']['samples'] if s['value']==8), 1.8)

    def test_oled_scan_commands_preserved(self):
        result = Runtime(self.sources, seconds=1, commands=[]).run()
        self.assertFalse(result['frames'][-1]['flip_x'])
        self.assertFalse(result['frames'][-1]['flip_y'])
        modified = dict(self.sources)
        modified['src/hal_entry.c'] = modified['src/hal_entry.c'].replace('OLED_DisplayTurn(1)', 'OLED_DisplayTurn(0)')
        result = Runtime(modified, seconds=1, commands=[]).run()
        self.assertTrue(result['frames'][-1]['flip_x'])
        self.assertTrue(result['frames'][-1]['flip_y'])

    def test_live_queue_waits_for_uart_and_keeps_program_state(self):
        inbox = queue.Queue(maxsize=1)
        paused = threading.Event()
        events = []
        runtime = LiveRuntime(self.sources, inbox, paused, lambda frame: None)
        runtime.limit_ms = 6000
        sent = []
        original_advance = runtime.advance
        def advance(amount):
            if not sent and runtime.uart_open and runtime.rx is not None:
                inbox.put('3'); sent.append('3')
            elif len(sent)==1 and runtime.rx is None:
                inbox.put('0'); sent.append('0')
            original_advance(amount)
            events.extend(e for e in runtime.events if 'UART' in e['text'] and e not in events)
        runtime.advance = advance
        with patch('simulator.live.time.sleep', lambda _: None):
            runtime.run()
        self.assertEqual([e['text'] for e in events], ['UART 收到字符 3', 'UART 收到字符 0'])
        self.assertGreater(events[1]['t'] - events[0]['t'], 2500)
        self.assertLessEqual(len(runtime.trace), 2)
        self.assertLess(len(runtime.events), 40)


if __name__ == '__main__': unittest.main()
