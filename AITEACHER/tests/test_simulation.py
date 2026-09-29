import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from simulator.engine import Runtime,SimulationError,load_sources


class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=load_sources(Path(__file__).resolve().parents[1]/'reference_projects'/'Dog')

    def simulate(self,sources=None,command='2',seconds=7):
        return Runtime(sources or self.original,seconds,[(1,command)] if command is not None else []).run()

    def test_reference_forward_executes_actual_loop(self):
        result=self.simulate()
        outputs=[e for e in result['events'] if e['t']>=1000 and ' = ' in e['text']]
        self.assertEqual(len(outputs),84) # 5 x 16 gait writes + 4 stand writes
        self.assertAlmostEqual(outputs[1]['t']-outputs[0]['t'],20)
        self.assertTrue(any(any(f['oled']) for f in result['frames']))
        self.assertTrue(any('数组越界' in w for w in result['warnings']))

    def test_code_edit_changes_cycles_and_delay(self):
        sources=dict(self.original)
        sources['src/action.c']=sources['src/action.c'].replace('i<5','i<1').replace('150, BSP_DELAY_UNITS_MILLISECONDS','450, BSP_DELAY_UNITS_MILLISECONDS')
        result=self.simulate(sources)
        outputs=[e for e in result['events'] if e['t']>=1000 and ' = ' in e['text']]
        self.assertEqual(len(outputs),20)
        self.assertAlmostEqual(outputs[4]['t']-outputs[3]['t'],450)

    def test_pwm_driver_arithmetic_changes_waveform(self):
        sources=dict(self.original)
        sources['src/PWM.c']=sources['src/PWM.c'].replace('(100 - duty)','(100 - duty - 1)')
        result=self.simulate(sources,command=None,seconds=2)
        self.assertAlmostEqual(result['frames'][-1]['duty']['R_Front']['percent'],8,places=3)

    def test_all_uart_actions_produce_code_outputs(self):
        for command in '0134567':
            with self.subTest(command=command):
                result=self.simulate(command=command,seconds=5)
                self.assertTrue(any('UART' in e['text'] for e in result['events']))
                if command=='5':self.assertIsNotNone(result['frames'][-1]['duty']['Tail'])

    def test_removing_uart_rearm_changes_input_handling(self):
        sources=dict(self.original)
        sources['src/hal_entry.c']=sources['src/hal_entry.c'].replace('R_SCI_UART_Read(&Blue_Tooth_ctrl,MODE,1);','')
        result=self.simulate(sources)
        self.assertTrue(any('未接收' in w for w in result['warnings']))
        self.assertFalse(any(e['t']>=1000 and ' = ' in e['text'] for e in result['events']))

    def test_unsupported_calls_fail_instead_of_playing_fake_animation(self):
        sources=dict(self.original)
        sources['src/action.c']=sources['src/action.c'].replace('void stand()','void stand()').replace('R_Rear_SetDuty(7);','unknown_device();',1)
        with self.assertRaisesRegex(SimulationError,'unknown_device'):
            self.simulate(sources)

    def test_fsp_period_change_affects_pulse_width(self):
        sources=dict(self.original)
        sources['ra_gen/hal_data.c']=sources['ra_gen/hal_data.c'].replace('0x1b7740','0x36ee80')
        result=self.simulate(sources,command=None,seconds=2)
        self.assertAlmostEqual(result['frames'][-1]['duty']['R_Front']['pulse_ms'],2.8,places=3)

    def test_function_scope_does_not_leak_caller_locals(self):
        sources=dict(self.original)
        sources['src/action.c']=sources['src/action.c'].replace('void stand()','int test_duty=7;\nvoid nested_test(){R_Rear_SetDuty(test_duty);}\nvoid stand()').replace('R_Rear_SetDuty(7);','int test_duty=3; nested_test();',1)
        result=self.simulate(sources,command=None,seconds=2)
        self.assertAlmostEqual(result['frames'][-1]['duty']['R_Rear']['percent'],7)

    def test_user_sources_unchanged(self):
        before=dict(self.original);self.simulate();self.assertEqual(self.original,before)


if __name__=='__main__':unittest.main()
