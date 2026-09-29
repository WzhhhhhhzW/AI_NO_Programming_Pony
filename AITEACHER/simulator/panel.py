"""打开即运行的 3D 实验室与虚拟蓝牙遥控。"""
import json
import math
import queue
import threading
from pathlib import Path
import sys
from loguru import logger

from PyQt6.QtCore import QObject, QThread, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QApplication
from simulator.engine import EndRun
from simulator.live import LiveRuntime, measure_inputs
from simulator.commands import discover_commands


def validate_payload(payload):
    """虚拟串口按字节发送，限制为适合课程工程的可见 ASCII 内容。"""
    if not isinstance(payload, str):
        return None, '发送内容无效。'
    payload = payload.strip()
    if not payload:
        return None, '请填写要发送的内容。'
    if len(payload) > 32:
        return None, '发送内容最多 32 个字符。'
    if any(ord(char) < 32 or ord(char) > 126 for char in payload):
        return None, '发送内容请使用数字、英文字母或英文符号。'
    return payload, ''


class LiveWorker(QThread):
    frame = pyqtSignal(dict)
    mapping = pyqtSignal(dict)
    commands = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, sources, parent=None):
        super().__init__(parent)
        self.sources = sources
        self.inbox = queue.Queue(maxsize=1)
        self.paused = threading.Event()

    def run(self):
        try:
            self.commands.emit(discover_commands(self.sources, self.isInterruptionRequested))
            self.mapping.emit(measure_inputs(self.sources, self.isInterruptionRequested))
            if not self.isInterruptionRequested():
                LiveRuntime(self.sources, self.inbox, self.paused, self.frame.emit,
                            self.isInterruptionRequested).run()
        except EndRun:
            pass
        except Exception as exc:
            self.failed.emit(str(exc))


class Bridge(QObject):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel = panel

    @pyqtSlot(str)
    def action(self, payload):
        self.panel.send_action(payload)

    @pyqtSlot(bool)
    def manual(self, enabled):
        if self.panel.worker:
            if enabled: self.panel.worker.paused.set()
            else: self.panel.worker.paused.clear()

    @pyqtSlot(str)
    def copyCode(self, code):
        QApplication.clipboard().setText(code)


class SimulationPanel(QWidget):
    idle = pyqtSignal()
    ai_action = pyqtSignal(str)

    def __init__(self, source_provider, parent=None):
        super().__init__(parent)
        self.source_provider = source_provider
        self.worker = None
        self.ready = False
        self.pending_reload = False
        self.frame = None
        self.mappings = None
        self.loaded_sources = None
        self.commands = []
        self.reported_ready = False
        self.physics_debug = {}
        self._debug_pending = False
        self._last_debug_time = -1
        self.code_dirty = True
        self.using_example = False
        self.last_error = ''
        self.action_serial = 0
        self.completed_serial = 0
        self.action_state = None
        self.last_action = None
        self.setObjectName('simulationPanel')
        self.theme = getattr(parent, 'current_theme', 'dark')
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0)
        bar = QHBoxLayout()
        self.source = QComboBox(); self.source.addItems(['当前工程（含未保存编辑）', '内置 Dog 实例'])
        self.source.currentIndexChanged.connect(self.reload)
        bar.addWidget(self.source)
        self.reload_button = QPushButton('重新载入代码'); self.reload_button.clicked.connect(self.reload); bar.addWidget(self.reload_button)
        self.angle_button = QPushButton('📐 角度测算'); self.angle_button.clicked.connect(self.open_angles);bar.addWidget(self.angle_button)
        bar.addStretch(); layout.addLayout(bar)
        self.status = QLabel('正在加载模型与代码…'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.web = QWebEngineView()
        self.web.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,False)
        self.channel = QWebChannel(self.web.page()); self.bridge = Bridge(self)
        self.channel.registerObject('controller', self.bridge); self.web.page().setWebChannel(self.channel)
        self.web.loadFinished.connect(self.loaded)
        root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
        self.web.load(QUrl.fromLocalFile(str(root/'simulator/assets/index.html')))
        layout.addWidget(self.web,1)
        self.rerun_timer=QTimer(self);self.rerun_timer.setSingleShot(True);self.rerun_timer.setInterval(500)
        self.rerun_timer.timeout.connect(self.reload)
        self.ai_action.connect(self.send_action)
        self.set_theme(self.theme)

    def set_theme(self, theme):
        self.theme = 'light' if theme == 'light' else 'dark'
        light = self.theme == 'light'
        bg, text, button, border, hover = (('#f4f7fb','#24374b','#ffffff','#b7c8d8','#e0edf6') if light else
                                           ('#111a25','#c8d8e7','#223347','#466078','#31506a'))
        self.setStyleSheet(f"""
            QWidget#simulationPanel {{background:{bg};}}
            QWidget#simulationPanel QLabel {{color:{text};font-weight:normal;}}
            QWidget#simulationPanel QPushButton, QWidget#simulationPanel QComboBox {{
                background:{button};color:{text};border:1px solid {border};border-radius:5px;padding:6px 10px;}}
            QWidget#simulationPanel QComboBox QAbstractItemView {{
                background:{button};color:{text};selection-background-color:{hover};selection-color:{text};}}
            QWidget#simulationPanel QPushButton:hover {{background:{hover};}}
            QWidget#simulationPanel QPushButton:disabled {{color:#788999;background:{bg};}}
        """)
        from PyQt6.QtGui import QColor
        self.web.page().setBackgroundColor(QColor(bg))
        if self.ready:
            self.js('setTheme', self.theme)

    def js(self, function, value):
        self.web.page().runJavaScript('window.'+function+' && window.'+function+'('+json.dumps(value,ensure_ascii=False)+');')

    def loaded(self, ok):
        self.ready=ok
        if ok:
            self.set_theme(self.theme)
            self.reload()
        else: self.status.setText('3D 页面加载失败，请检查安装包资源。')

    def ensure_loaded(self):
        if not self.ready: return
        try:
            sources,_=self.source_provider(self.source.currentIndex()==1)
        except Exception:
            self.reload(); return
        if self.worker is None or sources != self.loaded_sources: self.reload()

    def open_angles(self):
        self.js('openAngleTool', True)

    def mark_changed(self):
        if self.source.currentIndex()==0:
            self.code_dirty=True
            self.rerun_timer.start()

    def reload(self, *_):
        if not self.ready: return
        if self.worker:
            self.pending_reload=True
            self.worker.requestInterruption()
            return
        self.pending_reload=False
        self.frame=None; self.mappings=None; self.reported_ready=False
        self.physics_debug={}; self._debug_pending=False; self._last_debug_time=-1
        self.code_dirty=True; self.last_error=''; self.action_state=None
        self.commands=[]
        self.js('resetLive', True)
        try:
            sources,label=self.source_provider(self.source.currentIndex()==1)
        except Exception as exc:
            self.status.setText('无法载入：'+str(exc)); self.js('liveError',str(exc)); return
        self.loaded_sources=sources
        self.using_example=self.source.currentIndex()==1
        self.status.setText('正在载入代码和整数输入对应表：'+label)
        self.worker=LiveWorker(sources,self)
        self.worker.commands.connect(self.on_commands)
        self.worker.frame.connect(self.on_frame); self.worker.mapping.connect(self.on_mapping)
        self.worker.failed.connect(self.failed); self.worker.finished.connect(self.finished)
        self.worker.start()

    def on_commands(self, commands):
        if self.pending_reload: return
        self.commands=commands
        self.js('setCommands', commands)

    def on_mapping(self, data):
        if self.pending_reload: return
        self.mappings=data; self.js('setMappings',data)

    def on_frame(self, frame):
        if self.pending_reload: return
        self.frame=frame; self.js('setLiveFrame',frame)
        self.code_dirty=False
        now=float(frame.get('t') or 0)
        if not self._debug_pending and (self._last_debug_time < 0 or now-self._last_debug_time>=180):
            self._debug_pending=True; self._last_debug_time=now
            self.web.page().runJavaScript(
                'window.simDebug ? window.simDebug() : null', self._on_debug)
        state=self.action_state
        if state and not state.get('completed'):
            expected='UART 收到字符 '+state['payload']
            if any(event.get('text')==expected and float(event.get('t') or 0)>=state['requested_t']
                   for event in frame.get('events',[])):
                state['started']=True
            # 接收函数重新挂起代表这次同步动作函数已经返回。
            if state.get('started') and frame.get('receiving') and now>state['requested_t']+1:
                state['completed']=True
                self.completed_serial=state['serial']
                self._finish_action_result(state)
        if frame['receiving'] and not self.reported_ready:
            self.reported_ready=True
            logger.info('3D 实时代码已运行，虚拟 UART 接收就绪')
            self.web.page().runJavaScript(
                'JSON.stringify({ready:window.simReady,error:window.simError,physics:window.simDebug ? window.simDebug().physics.engine : null})',
                lambda result: logger.info('3D 页面状态：{}',result))
        pending=self.worker and not self.worker.inbox.empty()
        state='动作执行中；下一指令已排队' if pending else ('虚拟蓝牙已就绪 · 点击动作即可控制' if frame['receiving'] else '程序执行中 · 等待串口接收就绪')
        self.status.setText(state)

    def _on_debug(self, data):
        self._debug_pending=False
        if isinstance(data,dict):
            self.physics_debug=data
            action=self.action_state
            if action and not action.get('completed'):
                physics=data.get('physics') or {}
                action['peak_tilt']=max(float(action.get('peak_tilt') or 0),
                                        float(physics.get('tilt') or 0))
            elif action and action.get('completed'):
                # on_frame 先把画面数据发给网页；这里收到的是物理引擎消费该帧后的
                # 最终姿态，用它刷新动作结果，避免把上一帧误报为最终状态。
                self._finish_action_result(action)

    @staticmethod
    def _angle_delta(value, baseline):
        value=math.degrees(float(value or 0)-float(baseline or 0))
        return round((value+180)%360-180,2)

    def _finish_action_result(self, action):
        physics=(self.physics_debug.get('physics') or {}) if isinstance(self.physics_debug,dict) else {}
        position=physics.get('position') or [0,0,0]
        rotation=physics.get('rotation') or [0,0,0]
        start=action.get('position') or [0,0,0]
        while len(position)<3: position.append(0)
        while len(rotation)<3: rotation.append(0)
        while len(start)<3: start.append(0)
        self.last_action={
            'serial':action['serial'],'command':action['payload'],'completed':True,
            'duration_ms':round(float((self.frame or {}).get('t') or 0)-action['requested_t'],1),
            'delta_x_cm':round((float(position[0])-float(start[0]))*100,2),
            'delta_z_cm':round((float(position[2])-float(start[2]))*100,2),
            'heading_change_deg':self._angle_delta(rotation[1],action.get('heading')),
            'final_tilt_deg':round(float(physics.get('tilt') or 0),2),
            'peak_tilt_deg':round(max(float(action.get('peak_tilt') or 0),
                                      float(physics.get('tilt') or 0)),2),
            'contacts':int(physics.get('contacts') or 0),
            'joint_angles_deg':{k:round(float(v),2) for k,v in (physics.get('angles') or {}).items()},
        }

    def send_action(self, payload):
        payload, message = validate_payload(payload)
        if message:
            self.status.setText(message)
            return
        if not self.worker or self.pending_reload: return
        physics=(self.physics_debug.get('physics') or {}) if isinstance(self.physics_debug,dict) else {}
        position=list(physics.get('position') or [0,0,0])
        rotation=list(physics.get('rotation') or [0,0,0])
        self.action_serial+=1
        self.action_state={'serial':self.action_serial,'payload':payload[0],
                           'requested_t':float((self.frame or {}).get('t') or 0),
                           'position':position,'heading':rotation[1] if len(rotation)>1 else 0,
                           'peak_tilt':float(physics.get('tilt') or 0),
                           'started':False,'completed':False}
        self.worker.paused.clear()
        # 只保留最近一次操作；当前动作结束、源码重新 Read 后发送，避免丢包。
        try: self.worker.inbox.get_nowait()
        except queue.Empty: pass
        try: self.worker.inbox.put_nowait(payload)
        except queue.Full: pass
        shown = payload if len(payload) <= 12 else payload[:12]+'…'
        self.status.setText('已发送 “'+shown+'”；若程序尚未接收，将在串口就绪后逐字节发送。')

    def request_ai_action(self, payload):
        """Thread-safe entry used by the advisor worker."""
        self.ai_action.emit(payload)

    def ai_snapshot(self):
        """Return only plain data so the advisor thread never touches Qt widgets."""
        frame=self.frame or {}
        debug=self.physics_debug if isinstance(self.physics_debug,dict) else {}
        physics=debug.get('physics') or {}
        position=list(physics.get('position') or [0,0,0])
        rotation=list(physics.get('rotation') or [0,0,0])
        while len(position)<3: position.append(0)
        while len(rotation)<3: rotation.append(0)
        if self.last_error: status='error'
        elif self.code_dirty or not frame: status='loading'
        elif frame.get('receiving'): status='ready'
        else: status='running'
        duty={}
        for name,value in (frame.get('duty') or {}).items():
            if isinstance(value,dict):
                duty[name]={'percent':value.get('percent'),'pulse_ms':value.get('pulse_ms')}
        return {
            'available':True,'status':status,'code_current':not self.code_dirty,
            'source':'内置 Dog 标准工程' if self.using_example else '学生当前工程（含编辑器保存内容）',
            'time_ms':frame.get('t'),'receiving':bool(frame.get('receiving')),
            'supported_commands':[{'payload':c.get('payload'),'label':c.get('label')} for c in self.commands],
            'warnings':list(frame.get('warnings') or [])[-12:],
            'recent_events':list(frame.get('events') or [])[-16:],
            'servo_output':duty,
            'physics':{
                'engine':physics.get('engine'),'contacts':physics.get('contacts'),
                'x_cm':round(float(position[0])*100,2),'z_cm':round(float(position[2])*100,2),
                'heading_deg':round(math.degrees(float(rotation[1] or 0)),2),
                'roll_deg':round(math.degrees(float(rotation[0] or 0)),2),
                'pitch_deg':round(math.degrees(float(rotation[2] or 0)),2),
                'tilt_deg':round(float(physics.get('tilt') or 0),2),
                'peak_tilt_deg':round(float(physics.get('peakTilt') or 0),2),
                'joint_angles_deg':{k:round(float(v),2) for k,v in (physics.get('angles') or {}).items()},
                'settings':dict(physics.get('settings') or {}),
            },
            'action_serial':self.action_serial,'completed_serial':self.completed_serial,
            'last_action':dict(self.last_action) if self.last_action else None,
            'error':self.last_error or None,
        }

    def failed(self, message):
        logger.error('3D 仿真执行失败：{}',message)
        self.last_error=str(message); self.code_dirty=True
        self.status.setText('代码仿真停止：'+message); self.js('liveError',message)

    def finished(self):
        worker=self.worker;self.worker=None
        if worker: worker.deleteLater()
        if self.pending_reload:
            self.pending_reload=False
            self.reload()
        else: self.idle.emit()

    def stop(self):
        self.pending_reload=False; self.rerun_timer.stop()
        if self.worker: self.worker.requestInterruption()
