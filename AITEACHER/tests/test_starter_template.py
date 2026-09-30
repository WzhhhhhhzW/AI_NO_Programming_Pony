from pathlib import Path
import unittest
from simulator.engine import load_sources
from simulator.commands import discover_commands
class StarterTemplateTests(unittest.TestCase):
 def test_only_requested_starter_commands(self):
  root=Path(__file__).resolve().parents[1]
  sources=load_sources(root/'tools/templates/Robohorse')
  self.assertEqual({c['char'] for c in discover_commands(sources)},{'1','2'})
  for name in ('Turn_Left','Turn_Right','Shake_Tail','Shake_Hand','Gasp'):
   self.assertNotIn(name,sources['src/action.c'])
   self.assertNotIn(name,sources['src/action.h'])
  reference=load_sources(root/'reference_projects/Dog')
  self.assertEqual({c['char'] for c in discover_commands(reference)},set('01234567'))
if __name__=='__main__':unittest.main()
