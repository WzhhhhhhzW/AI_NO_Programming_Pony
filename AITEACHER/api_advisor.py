"""使用用户配置的 Chat Completions 服务进行受限工程读写。"""
import asyncio
import fnmatch
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from openai import AsyncOpenAI
from loguru import logger
from advisor import Advisor, _under, WRITABLE_EXT
from dog_reference import DogReference


def tool_schema(name, description, properties, required=()):
    return {'type':'function','function':{'name':name,'description':description,
            'parameters':{'type':'object','properties':{k:{'type':v} for k,v in properties.items()},
                          'required':list(required),'additionalProperties':False}}}


TOOLS = [
    tool_schema('Read','读取工程文本文件，返回行号。修改前必须读取。',{'file_path':'string','offset':'integer','limit':'integer'},['file_path']),
    tool_schema('Glob','列出工程内匹配的源码/配置文件，例如 src/**/*.c。',{'pattern':'string'},['pattern']),
    tool_schema('Grep','在工程文本文件中查找字面字符串。',{'pattern':'string','glob':'string'},['pattern']),
    tool_schema('ReadReference','读取随软件发布且可运行的 Dog 标准工程源码。新增或修改动作前必须按动作名称查询。',{'query':'string'},['query']),
    tool_schema('ReadSimulation','读取当前工程的 3D 仿真结果；command 可填写一个蓝牙指令字符，工具会发送并等待动作结束，再返回位移、航向变化、倾斜、接触点和关节角。',{'command':'string'}),
    tool_schema('Edit','精确替换已读取的 src 源文件中的唯一文本；不允许新建或整文件覆盖。',{'file_path':'string','old_string':'string','new_string':'string'},['file_path','old_string','new_string']),
    tool_schema('compile_project','使用上位机编译器自检。不带参数检查工程，file 参数仅检查对应源文件。',{'file':'string'}),
]


class APIAdvisor(Advisor):
    def __init__(self, cfg, parent=None, power=1):
        super().__init__(cfg,parent)
        self.power=power
        self.read_versions={}
        self.messages=[{'role':'system','content':cfg.system_prompt}]
        self._serve_task=None

    def shutdown(self):
        self.requestInterruption()
        self.blockSignals(True)
        if self._loop and self._serve_task and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(self._serve_task.cancel)
            except RuntimeError:
                pass  # 请求结束时线程可能已经自行关闭事件循环。
        self.wait(5000)

    def path(self, value, write=False):
        root=Path(self.cfg.project_root).resolve()
        path=Path(value)
        if not path.is_absolute(): path=root/path
        path=path.resolve()
        if not path.is_relative_to(root): raise ValueError('路径不在当前工程内')
        if write and (path.suffix.lower() not in WRITABLE_EXT or not _under(str(path),self.cfg.write_roots)):
            raise ValueError('仅允许修改当前工程 src/ 下已有的 C/C++ 源文件')
        if not path.is_file(): raise ValueError('文件不存在；需要新文件时请在文件树中创建')
        if path.stat().st_size>1024*1024: raise ValueError('文件过大，请选择源码文件')
        return path

    def files(self, pattern='*'):
        root=Path(self.cfg.project_root).resolve()
        count=0
        for folder,dirs,files in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if d not in {'.git','.venv','Debug','Release','node_modules'}
                     and not (getattr(Path(folder,d).lstat(),'st_file_attributes',0) & 1024)]
            for name in files:
                path=Path(folder,name)
                if path.suffix.lower() not in {'.c','.h','.cpp','.hpp','.md','.txt','.xml','.json','.cfg'}: continue
                rel=path.relative_to(root).as_posix()
                if fnmatch.fnmatch(rel,pattern) or fnmatch.fnmatch(rel,pattern.replace('**/','')):
                    try: yield self.path(rel)
                    except ValueError: continue
                    count+=1
                    if count>=500: return

    @staticmethod
    def decode(data):
        for encoding in ('utf-8-sig','gb18030'):
            try: return data.decode(encoding), ('utf-8-sig' if data.startswith(b'\xef\xbb\xbf') else 'utf-8') if encoding=='utf-8-sig' else encoding
            except UnicodeDecodeError: pass
        raise ValueError('文件不是支持的文本编码')

    async def execute_tool(self, name, args):
        if self.isInterruptionRequested(): raise asyncio.CancelledError()
        if name not in self.cfg.allowed_tools: raise ValueError('当前模式不允许此工具：'+name)
        labels={'ReadReference':'读取标准工程','ReadSimulation':'读取仿真结果'}
        icons={'Edit':'✏️','compile_project':'🔨','ReadReference':'🐎','ReadSimulation':'🧪'}
        detail=str(args.get('file_path') or args.get('pattern') or args.get('query') or args.get('command') or '')
        self.tool.emit(icons.get(name,'🔎'),labels.get(name,name),detail)
        if name=='Read':
            path=self.path(args['file_path']);data=path.read_bytes();text,_=self.decode(data)
            self.read_versions[str(path)]=data
            offset=max(1,int(args.get('offset',1)));limit=max(1,min(500,int(args.get('limit',300))))
            return '\n'.join(f'{i+1}: {line}' for i,line in enumerate(text.splitlines()) if offset<=i+1<offset+limit)[:30000]
        if name=='Glob': return '\n'.join(str(p.relative_to(Path(self.cfg.project_root).resolve())) for p in self.files(args['pattern']))
        if name=='Grep':
            out=[]
            for path in self.files(args.get('glob','*')):
                text,_=self.decode(path.read_bytes())
                for i,line in enumerate(text.splitlines(),1):
                    if args['pattern'] in line: out.append(f'{path.relative_to(Path(self.cfg.project_root).resolve())}:{i}: {line[:400]}')
                    if len(out)>=100: return '\n'.join(out)
            return '\n'.join(out) or '未找到匹配'
        if name=='ReadReference':
            return DogReference().tool_context(args['query'])
        if name=='ReadSimulation':
            provider=self.cfg.simulation_provider
            if not callable(provider):
                return json.dumps({'available':False,'status':'unavailable',
                                   'message':'当前界面没有可读取的仿真环境。'},ensure_ascii=False)
            command=str(args.get('command') or '').strip()
            if command and (len(command)!=1 or ord(command)<32 or ord(command)>126):
                raise ValueError('仿真指令必须是一个可见 ASCII 字符，例如 3 或 L')

            snapshot=provider()
            if not isinstance(snapshot,dict) or not snapshot.get('available'):
                return json.dumps(snapshot or {'available':False,'status':'unavailable'},ensure_ascii=False)
            # 源码重载和物理场景初始化需要一点时间。动作必须在当前代码已加载后发送。
            for _ in range(48):
                if snapshot.get('status') in ('ready','running') and snapshot.get('code_current'):
                    break
                if snapshot.get('status')=='error':
                    return json.dumps(snapshot,ensure_ascii=False)
                await asyncio.sleep(.25)
                snapshot=provider()
            if not command:
                return json.dumps(snapshot,ensure_ascii=False)
            if not snapshot.get('code_current') or snapshot.get('status') not in ('ready','running'):
                snapshot['tool_warning']='当前工程尚未完成仿真加载，未发送指令。'
                return json.dumps(snapshot,ensure_ascii=False)

            before=int(snapshot.get('action_serial') or 0)
            provider(command)
            for _ in range(100):
                await asyncio.sleep(.25)
                snapshot=provider()
                serial=int(snapshot.get('action_serial') or 0)
                completed=int(snapshot.get('completed_serial') or 0)
                if serial>before and completed>=serial:
                    # 等待一次物理调试快照，把最后一帧姿态纳入结果。
                    await asyncio.sleep(.3)
                    return json.dumps(provider(),ensure_ascii=False)
                if snapshot.get('status')=='error':
                    return json.dumps(snapshot,ensure_ascii=False)
            snapshot['tool_warning']='仿真动作等待超时；不能据此声称动作已经验证。'
            return json.dumps(snapshot,ensure_ascii=False)
        if name=='Edit':
            if 'Edit' not in self.cfg.allowed_tools: raise ValueError('当前模式不允许修改文件')
            path=self.path(args['file_path'],write=True);data=path.read_bytes()
            if self.read_versions.get(str(path))!=data: raise ValueError('请先重新 Read 此文件；文件可能已经变化')
            text,encoding=self.decode(data)
            # API 文本统一 LF；写回时保留原文件换行与编码。
            newline='\r\n' if '\r\n' in text else '\n';text=text.replace('\r\n','\n')
            old=args['old_string'].replace('\r\n','\n');new=args['new_string'].replace('\r\n','\n')
            if not old or text.count(old)!=1: raise ValueError('old_string 必须准确匹配唯一位置，请重新 Read')
            changed=text.replace(old,new,1).replace('\n',newline).encode(encoding)
            if self.isInterruptionRequested(): raise asyncio.CancelledError()
            if path.read_bytes()!=data: raise ValueError('文件已变化，取消本次修改')
            path.write_bytes(changed);self.read_versions[str(path)]=changed;self.edited.emit(str(path))
            return '修改已写入。请调用 compile_project 自检。'
        if name=='compile_project':
            from build_tool import compile_once,check_file,format_result
            file=args.get('file','')
            if file:
                path=self.path(file)
                if path.suffix.lower() not in WRITABLE_EXT: raise ValueError('仅支持源文件检查')
                result=await asyncio.to_thread(check_file,self.cfg.project_root,str(path.relative_to(Path(self.cfg.project_root).resolve())))
            else: result=await asyncio.to_thread(compile_once,self.cfg.project_root)
            return format_result(result)
        raise ValueError('不支持的工具：'+name)

    async def _serve(self):
        self._serve_task=asyncio.current_task()
        try:
            await self._serve_session()
        except asyncio.CancelledError:
            pass

    async def _serve_session(self):
        from config import api_config_error
        problem=api_config_error(self.cfg.api_key,self.cfg.base_url,self.cfg.model)
        if problem: raise ValueError(problem)
        self._inbox=asyncio.Queue();self._alive=True;self.started_ok.emit()
        while not self._pending.empty(): self._inbox.put_nowait(self._pending.get())
        logger.info('AI 使用用户配置端点 host={} model={}',urlsplit(self.cfg.base_url).hostname,self.cfg.model)
        async with AsyncOpenAI(base_url=self.cfg.base_url,api_key=self.cfg.api_key,timeout=60,max_retries=0,
                               http_client=httpx.AsyncClient(follow_redirects=False)) as client:
            while not self.isInterruptionRequested():
                item=await self._inbox.get()
                if item is self._STOP: break
                start=len(self.messages)
                try: await self._one_turn(client,item)
                except Exception as exc:
                    # 出错轮次不能留下缺少 tool 回复的会话结构；已写入文件仍由 UI 快照撤销。
                    self.messages=self.messages[:start]
                    message=str(exc).replace(self.cfg.api_key,'[已隐藏]')
                    logger.error('AI 请求失败：{}',message)
                    self.failed.emit(message or type(exc).__name__)

    async def _one_turn(self,client,question):
        from project_evidence import project_evidence
        evidence=project_evidence(self.cfg.project_root,question)
        self.messages.append({'role':'user','content':evidence+'\n\n【学生本次问题】\n'+question})
        self.read_versions.clear()
        options={}
        if urlsplit(self.cfg.base_url).hostname=='api.deepseek.com':
            options={'extra_body':{'thinking':{'type':'disabled' if self.power==0 else 'enabled'}}}
            if self.power: options['reasoning_effort']='low' if self.power==1 else 'high'
        for _ in range(self.cfg.max_turns):
            if self.isInterruptionRequested(): return
            self.thinking.emit()
            response=await client.chat.completions.create(model=self.cfg.model,messages=self.messages,
                        tools=[t for t in TOOLS if t['function']['name'] in self.cfg.allowed_tools],max_tokens=8192,**options)
            if not response.choices: raise ValueError('API 未返回回答，请检查模型配置')
            choice=response.choices[0];message=choice.message
            if choice.finish_reason=='length': raise ValueError('模型输出达到长度上限，本轮未执行截断的工具请求')
            saved={'role':'assistant','content':message.content or ''}
            reasoning=getattr(message,'reasoning_content',None)
            if reasoning is not None: saved['reasoning_content']=reasoning
            calls=message.tool_calls or []
            if calls: saved['tool_calls']=[c.model_dump(exclude_none=True) for c in calls]
            self.messages.append(saved)
            if message.content: self.text.emit(message.content)
            if not calls:
                if not message.content: raise ValueError('API 未返回正文，请检查模型和服务状态')
                self.turn_done.emit('已完成');return
            for call in calls:
                try: result=await self.execute_tool(call.function.name,json.loads(call.function.arguments))
                except asyncio.CancelledError: return
                except Exception as exc:
                    result='工具未执行：'+str(exc)
                    self.denied.emit(call.function.name,result)
                self.messages.append({'role':'tool','tool_call_id':call.id,'content':result})
        raise ValueError('本轮达到工具调用次数限制；请检查已有改动后继续提问')
