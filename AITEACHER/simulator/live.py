"""持续执行同一份 C 程序，实时串口输入；动作之间保留变量、外设和姿态。"""
import queue
import time
from collections import deque

from simulator.engine import Runtime, SimulationError, EndRun


JOINTS = ('R_Front', 'L_Front', 'R_Rear', 'L_Rear', 'Tail')


def measure_inputs(sources, cancelled=lambda: False):
    """执行工程自己的 SetDuty 函数，测得整数输入表，不假定固定换算公式。"""
    runtime = Runtime(sources, commands=[], cancelled=cancelled)
    for timer in runtime.timers.values():
        timer['open'] = timer['start'] = True
    mappings = {}
    for joint in JOINTS:
        samples = []
        try:
            for value in range(101):
                if cancelled(): raise EndRun()
                runtime.duties[joint] = None
                runtime.call(joint + '_SetDuty', [value])
                output = runtime.duties[joint]
                if output and .5 <= output['pulse_ms'] <= 2.5:
                    samples.append(dict(output, value=value))
            mappings[joint] = {'samples': samples}
        except SimulationError as exc:
            mappings[joint] = {'samples': [], 'error': str(exc)}
    return mappings


class LiveRuntime(Runtime):
    def __init__(self, sources, inbox, paused, emit, cancelled=lambda: False):
        self.inbox, self.paused, self.emit = inbox, paused, emit
        self.pending_input = deque()
        self.last_emit = 0
        super().__init__(sources, commands=[], cancelled=cancelled)
        self.limit_ms = float('inf')
        self.budget_clock = 0

    def take_input(self):
        """每次串口接收一个字节；新按键会替换尚未发完的旧内容。"""
        try:
            payload = self.inbox.get_nowait()
            self.pending_input = deque(payload)
        except queue.Empty:
            pass
        return self.pending_input.popleft() if self.pending_input else None

    def snapshot(self, coord=''):
        # 实时会话只保留当前帧和近期事件，避免长时间运行累积内存。
        self.trace = self.trace[-1:]
        self.events = self.events[-30:]
        super().snapshot(coord)

    def publish(self, force=False):
        now = time.monotonic()
        if force or now - self.last_emit >= .04:
            frame = dict(self.trace[-1])
            frame.update(t=self.clock, warnings=list(self.warnings),
                         receiving=self.uart_open and self.rx is not None,
                         events=list(self.events))
            self.emit(frame)
            self.last_emit = now

    def advance(self, amount):
        if amount < 0: raise SimulationError('延时不能为负数')
        remaining = amount
        while remaining > 0:
            if self.cancelled(): raise EndRun()
            if self.paused.is_set():
                start = time.monotonic()
                time.sleep(.02)
                self.started += time.monotonic() - start
                continue
            # 按真实时间推进延时，并在延时期间处理实际 UART 回调。
            step = min(20, remaining)
            start = time.monotonic()
            time.sleep(step / 1000)
            self.started += time.monotonic() - start
            try:
                if not self.uart_open or self.rx is None: raise queue.Empty
                char = self.take_input()
                if char is None: raise queue.Empty
                self.commands.append((self.clock, ord(char)))
            except queue.Empty:
                pass
            super().advance(step)
            remaining -= step
            self.publish()
            if self.clock - self.budget_clock >= 1000:
                self.budget_clock = self.clock
                self.steps = 0
                self.started = time.monotonic()

    def run(self):
        result = super().run()
        self.publish(force=True)
        return result
