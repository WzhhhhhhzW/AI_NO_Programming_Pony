"""生成标准源码实际输出，用于连续转向物理回归。"""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from simulator.engine import Runtime,load_sources
root=Path(__file__).resolve().parents[1]
sources=load_sources(root/'reference_projects/Dog')
results={}
for name,chars in [('left','333333'),('right','444444'),('mixed','343434')]:
    result=Runtime(sources,27,[(1+4*i,ch) for i,ch in enumerate(chars)]).run()
    received=[e for e in result['events'] if 'UART 收到' in e['text']]
    assert len(received)==6, (name,len(received))
    results[name]=dict(duration=result['duration'],frames=[dict(t=f['t'],duty=f['duty']) for f in result['frames']])
(root/'build/turn_traces_long.json').write_text(json.dumps(results),encoding='utf-8')
print('PASS: 18 UART commands executed from unchanged standard C source.')
