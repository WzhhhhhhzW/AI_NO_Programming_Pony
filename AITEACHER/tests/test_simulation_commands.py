from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from simulator.engine import load_sources
from simulator.commands import discover_commands


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.sources=load_sources(str(Path(__file__).resolve().parents[1]/'reference_projects/Dog'))

    def test_original_eight_commands(self):
        self.assertEqual({c['char'] for c in discover_commands(self.sources)},set('01234567'))

    def test_added_removed_and_remapped_backward(self):
        original=self.sources['src/hal_entry.c']
        for number in (8,9):
            self.sources['src/hal_entry.c']=original.replace('case Stand_mode:',f'case {number}: Backward(); break;\n case Stand_mode:')+'\nvoid Backward(void) { stand(); }\n'
            commands=discover_commands(self.sources)
            self.assertIn({'char':str(number),'label':'↓ 后退'},commands)
        self.sources['src/hal_entry.c']=original
        self.assertNotIn('8',{c['char'] for c in discover_commands(self.sources)})

    def test_ascii_callback_mapping(self):
        s=self.sources['src/hal_entry.c']
        s=s.replace("MODE[0] = MODE[0] - '0';",'')
        s=s.replace('case Stand_mode:',"case 'B': Backward(); break;\n case Stand_mode:")
        self.sources['src/hal_entry.c']=s+'\nvoid Backward(void) { stand(); }\n'
        self.assertIn({'char':'B','label':'↓ 后退'},discover_commands(self.sources))

    def test_ai_left_turn_name_is_not_overridden_by_final_stand(self):
        for path, source in list(self.sources.items()):
            self.sources[path] = source.replace('Turn_Left', 'LeftTurn')
        commands = discover_commands(self.sources)
        self.assertIn({'char':'3','label':'↶ 左转'}, commands)
        self.assertNotIn({'char':'3','label':'站立'}, commands)

    def test_wag_tail_camel_case_has_friendly_label(self):
        original=self.sources['src/hal_entry.c']
        self.sources['src/hal_entry.c']=original.replace(
            'case Stand_mode:', 'case 8: WagTail(); break;\n case Stand_mode:'
        )+'\nvoid WagTail(void) { stand(); }\n'
        self.assertIn({'char':'8','label':'摇尾巴'},discover_commands(self.sources))

    def test_unknown_action_is_not_mislabeled_as_stand(self):
        original=self.sources['src/hal_entry.c']
        self.sources['src/hal_entry.c']=original.replace(
            'case Stand_mode:', 'case 8: CustomDance(); stand(); break;\n case Stand_mode:'
        )+'\nvoid CustomDance(void) { stand(); }\n'
        self.assertIn({'char':'8','label':'CustomDance'},discover_commands(self.sources))

if __name__=='__main__': unittest.main()
