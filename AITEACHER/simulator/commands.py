"""Discover commands from the same parsed Dog program used by the simulator."""
import copy
import re
from pycparser import c_ast as C
from simulator.engine import Runtime, Cell, Ref, SimulationError, EndRun


def walk(node):
    if node is None: return
    yield node
    for _, child in node.children(): yield from walk(child)


LABELS = {
    'backward': '↓ 后退', 'back': '↓ 后退', 'reverse': '↓ 后退',
    'forwardold': '↑ 前进', 'forward': '↑ 前进',
    'turnleft': '↶ 左转', 'leftturn': '↶ 左转',
    'turnright': '右转 ↷', 'rightturn': '右转 ↷',
    'sleep': '趴下', 'shaketail': '摇尾巴', 'wagtail': '摇尾巴',
    'tailwag': '摇尾巴', 'shakehand': '握手', 'handshake': '握手',
    'gasp': '哈气', 'stand': '站立',
}


def action_label(function_name):
    """Map common C naming styles to one student-facing action name.

    AI generated projects use both ``Turn_Left`` and ``LeftTurn``.  Compacting
    separators and camel-case makes those equivalent.  The small heuristics
    also cover names such as ``Action_LeftTurn`` without guessing from servo
    helper functions.
    """
    compact = re.sub(r'[^a-z0-9]', '', function_name.casefold())
    if compact in LABELS:
        return LABELS[compact]
    if 'turn' in compact and 'left' in compact:
        return '↶ 左转'
    if 'turn' in compact and 'right' in compact:
        return '右转 ↷'
    if 'tail' in compact and ('wag' in compact or 'shake' in compact):
        return '摇尾巴'
    if 'backward' in compact or 'reverse' in compact:
        return '↓ 后退'
    if 'forward' in compact:
        return '↑ 前进'
    return None


def discover_commands(sources, cancelled=lambda: False):
    runtime = Runtime(sources, commands=[], cancelled=cancelled)
    entry = runtime.functions.get('hal_entry')
    branches = []
    for node in walk(entry):
        if not isinstance(node, C.Switch): continue
        # Dog UART callback receives into MODE[0]; unrelated switches are excluded.
        cond = node.cond
        if not (isinstance(cond,C.ArrayRef) and isinstance(cond.name,C.ID)
                and cond.name.name=='MODE' and runtime.eval(cond.subscript)==0): continue
        for case in node.stmt.block_items or []:
            if not isinstance(case,C.Case): continue
            value = int(runtime.eval(case.expr))
            calls = [n.name.name for n in walk(case) if isinstance(n,C.FuncCall) and isinstance(n.name,C.ID)]
            calls = [name for name in calls if name in runtime.functions and not name.startswith(('OLED_', 'Face_', 'R_'))]
            # A branch often ends with stand() to restore the neutral pose.
            # Prefer the real action and only expose "站立" when it is the
            # branch's sole recognised action.  Unknown actions keep their
            # function name instead of being mislabeled as stand.
            labelled = [(name, action_label(name)) for name in calls]
            label = next((label for _name, label in labelled
                          if label and label != '站立'), None)
            if label is None:
                non_stand = next((name for name, known in labelled
                                  if known != '站立'), None)
                label = (non_stand or
                         next((known for _name, known in labelled if known), None) or
                         f'指令 {value}')
            branches.append((value,label))
    if not branches: return []
    baseline = copy.deepcopy(runtime.globals)
    commands = []
    seen = set()
    for value,label in branches:
        # Check both ASCII cases and the standard digit-to-mode conversion against
        # the actual callback, rather than assuming the old 0..7 mapping.
        for byte in dict.fromkeys((value+ord('0'),value)):
            if not 32 <= byte <= 126: continue
            if cancelled(): raise EndRun()
            runtime.globals=copy.deepcopy(baseline)
            runtime.globals['MODE'].value[0].set(byte)
            try:
                runtime.call('Blue_Tooth_Callback',[Ref(Cell({'event':Cell(1),'data':Cell(byte)}))])
            except SimulationError:
                continue
            if runtime.globals['MODE'].value[0].value==value and chr(byte) not in seen:
                commands.append({'char':chr(byte),'label':label})
                seen.add(chr(byte));break
    rank={'↶ 左转':0,'↑ 前进':1,'右转 ↷':2,'↓ 后退':3,'趴下':4,'站立':5,'摇尾巴':6,'握手':7,'哈气':8}
    return sorted(commands,key=lambda c:rank.get(c['label'],9))
