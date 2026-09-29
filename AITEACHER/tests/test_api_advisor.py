"""Configured API only; project edit boundaries and multi-turn tool protocol."""
import asyncio
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

_config=tempfile.TemporaryDirectory(prefix='horse-api-tests-',ignore_cleanup_errors=True)
os.environ['APPDATA']=_config.name

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advisor import AdvisorConfig, EDIT_TOOLS
from api_advisor import APIAdvisor
from config import api_config_error, DEFAULT_API_KEY, DEFAULT_API_BASE_URL, DEFAULT_ENDPOINT_ID
from openai.types.chat import ChatCompletion


class APITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        (self.root/'src').mkdir()
        self.file=self.root/'src/main.c'
        self.file.write_bytes(b'int speed = 1;\r\n')
        self.cfg=AdvisorConfig(project_root=str(self.root),system_prompt='Test',
            base_url='https://api.deepseek.com',api_key='synthetic-test-key',model='chosen-model',
            allowed_tools=EDIT_TOOLS+['ReadReference','ReadSimulation','compile_project'],
            write_roots=[str(self.root/'src')],max_turns=4)
        self.agent=APIAdvisor(self.cfg)

    def tearDown(self):
        self.temp.cleanup()

    async def read(self):
        return await self.agent.execute_tool('Read',{'file_path':'src/main.c'})

    async def edit(self,**overrides):
        args=dict(file_path='src/main.c',old_string='speed = 1',new_string='speed = 2')
        args.update(overrides)
        return await self.agent.execute_tool('Edit',args)

    def test_no_defaults_and_required_fields(self):
        self.assertEqual((DEFAULT_API_KEY,DEFAULT_API_BASE_URL,DEFAULT_ENDPOINT_ID),('','',''))
        for key,url,model in [('',self.cfg.base_url,'m'),('k','','m'),('k',self.cfg.base_url,''),
                              ('k','https://platform.deepseek.com','m'),('k','https://[bad','m')]:
            self.assertTrue(api_config_error(key,url,model))
        self.assertEqual(api_config_error('k',self.cfg.base_url,'m'),'')

    async def test_read_required_and_original_newline_preserved(self):
        with self.assertRaises(ValueError): await self.edit()
        await self.read()
        await self.edit()
        self.assertEqual(self.file.read_bytes(),b'int speed = 2;\r\n')

    async def test_stale_file_and_nonunique_replacement_rejected(self):
        await self.read()
        self.file.write_bytes(b'int speed = 1; int speed = 1;\r\n')
        with self.assertRaises(ValueError): await self.edit()
        await self.read()
        with self.assertRaises(ValueError): await self.edit()
        self.assertEqual(self.file.read_bytes(),b'int speed = 1; int speed = 1;\r\n')

    async def test_write_and_read_boundaries(self):
        (self.root/'ra_gen').mkdir()
        (self.root/'ra_gen/generated.c').write_text('int speed = 1;')
        (self.root/'src/config.json').write_text('{}')
        for path in ('../outside.c','ra_gen/generated.c','src/config.json','src/new.c'):
            with self.assertRaises(ValueError): await self.edit(file_path=path)
        with self.assertRaises(ValueError):
            await self.agent.execute_tool('Read',{'file_path':'../outside.c'})
        await self.read()
        self.cfg.allowed_tools=['Read']
        with self.assertRaises(ValueError): await self.edit()
        with self.assertRaises(ValueError): await self.agent.execute_tool('compile_project',{})

    async def test_tool_history_preserves_reasoning_and_selected_model(self):
        def response(message,finish):
            return ChatCompletion.model_validate(dict(id='test',object='chat.completion',created=0,
                model='chosen-model',choices=[dict(index=0,finish_reason=finish,message=message)]))
        call={'id':'read-1','type':'function','function':{'name':'Read','arguments':json.dumps({'file_path':'src/main.c'})}}
        answers=[response(dict(role='assistant',content='',reasoning_content='test reasoning',tool_calls=[call]),'tool_calls'),
                 response(dict(role='assistant',content='Read complete.'),'stop')]
        recorded=[]
        async def create(**kwargs):
            recorded.append(copy.deepcopy(kwargs))
            return answers.pop(0)
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        await self.agent._one_turn(client,'Read the test file')
        self.assertEqual(recorded[1]['messages'][2]['reasoning_content'],'test reasoning')
        self.assertEqual(recorded[1]['messages'][3]['tool_call_id'],'read-1')
        self.assertTrue(all(r['model']=='chosen-model' for r in recorded))
        self.assertIn('speed = 1',recorded[1]['messages'][3]['content'])

    async def test_reference_tool_returns_verified_turn_source(self):
        result=await self.agent.execute_tool('ReadReference',{'query':'左转'})
        self.assertIn('Dog/src/action.c',result)
        self.assertIn('void Turn_Left()',result)
        self.assertIn('case Turn_Left_mode:',result)

    async def test_simulation_tool_sends_command_and_waits_for_result(self):
        state={'action_serial':0,'completed_serial':0,'polls':0}
        calls=[]
        def provider(command=None):
            if command:
                calls.append(command);state['action_serial']+=1;state['polls']=0
            else:
                state['polls']+=1
                if state['action_serial'] and state['polls']>=2:
                    state['completed_serial']=state['action_serial']
            return {'available':True,'status':'ready','code_current':True,
                    **state,'last_action':({'completed':True,'command':'3',
                    'heading_change_deg':-18.5,'peak_tilt_deg':4.2,'contacts':4}
                    if state['completed_serial'] else None)}
        self.cfg.simulation_provider=provider
        result=json.loads(await self.agent.execute_tool('ReadSimulation',{'command':'3'}))
        self.assertEqual(calls,['3'])
        self.assertEqual(result['completed_serial'],1)
        self.assertEqual(result['last_action']['heading_change_deg'],-18.5)


if __name__=='__main__': unittest.main()
