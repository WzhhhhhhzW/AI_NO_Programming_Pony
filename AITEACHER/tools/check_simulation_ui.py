"""隔离配置的真实 Qt 仿真界面验证；不联网，不打开学生工程。"""
import os
from pathlib import Path
import sys
import tempfile
import time
import json

os.environ['APPDATA']=tempfile.mkdtemp(prefix='horse-sim-ui-')
os.environ['QT_QPA_PLATFORM']=os.environ.get('SIM_TEST_PLATFORM','offscreen')
os.environ['QTWEBENGINE_CHROMIUM_FLAGS']='' if os.environ['QT_QPA_PLATFORM']=='windows' else '--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts,True)
from ui_main import CoderUI

app=QApplication(['sim-ui-check'])
for f in ('msyh.ttc','consola.ttf','segoeui.ttf','seguiemj.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+f)
w=CoderUI();w.resize(1600,950);w.show();w.open_simulation()
panel=w.simulation
def wait(predicate,timeout=30):
    start=time.monotonic()
    while not predicate():
        app.processEvents();time.sleep(.01)
        if time.monotonic()-start>timeout:raise TimeoutError('UI check timed out')
def js(code):
    result=[];panel.web.page().runJavaScript(code,lambda r:result.append(r));wait(lambda:bool(result));return result[0]
try:
    wait(lambda:panel.ready)
    wait(lambda:panel.frame is not None and panel.frame['receiving'] and panel.frame['t']>1200)
    print('JS BOOT',js('JSON.stringify({error:window.simError,ready:window.simReady})'),flush=True)
    wait(lambda:bool(js('window.simReady===true')))
    assert panel.mappings
    assert abs(js('window.simDebug().angles.Tail')) < 1
    print('AUTOLOAD',js('JSON.stringify({ready:window.simDebug().ready,physics:window.simDebug().physics})'),flush=True)
    panel.web.grab().save(str(Path('build/simulation_ready_v16_3.png').resolve()))
    js("document.getElementById('showCustom').click();document.getElementById('customLabel').value='测试左转';document.getElementById('customPayload').value='3';document.getElementById('saveCustom').click();")
    assert js("document.querySelectorAll('#customRemote .send-command').length") == 1
    assert js("document.querySelector('#customRemote .send-command').textContent.includes('测试左转')")
    assert js("JSON.parse(localStorage.getItem('horse-custom-remote-v1'))[0].payload") == '3'
    panel.web.grab().save(str(Path('build/simulation_custom_remote.png').resolve()))
    before=sum('UART 收到字符 3' in e['text'] for e in panel.frame['events'])
    js("document.querySelector('#customRemote .send-command').click()")
    wait(lambda:sum('UART 收到字符 3' in e['text'] for e in panel.frame['events'])>before)
    wait(lambda:panel.frame['receiving'],timeout=30)
    js("document.querySelector('#customRemote .delete-custom').click()")
    assert js("document.querySelectorAll('#customRemote .send-command').length") == 0
    print('CUSTOM REMOTE: create, persist, send and delete passed.',flush=True)
    assert js('document.getElementById("action_3").disabled') is False
    serial=panel.action_serial
    js('document.getElementById("action_3").click()')
    wait(lambda:any('UART 收到字符 3' in e['text'] for e in panel.frame['events']))
    wait(lambda:panel.completed_serial>serial,timeout=30)
    start=panel.frame['t']
    wait(lambda:panel.frame['t']>start+3800,timeout=30)
    print('LEFT',js('JSON.stringify(window.simDebug().physics)'),flush=True)
    assert panel.ai_snapshot()['last_action']['completed'] is True
    assert abs(panel.ai_snapshot()['last_action']['heading_change_deg'])>1
    assert js('window.simDebug().physics.peakTilt') < 35
    assert js('Number(document.getElementById("servoSpeed").value)') == 180
    headings=[]
    for command in ('4','3'):
        serial=panel.action_serial
        js('document.getElementById("action_'+command+'").click()')
        wait(lambda:panel.completed_serial>serial,timeout=30)
        headings.append(panel.ai_snapshot()['last_action']['heading_change_deg'])
        assert js('window.simDebug().physics.peakTilt') < 35
    assert headings[0]*headings[1]<0, headings
    print('AI SNAPSHOT TURN HEADINGS',headings,flush=True)
    print('TURN STABILITY',js('JSON.stringify(window.simDebug().physics)'),flush=True)
    w.grab().save(str(Path('build/simulation_v16_3.png').resolve()))
    start=panel.frame['t']
    js('document.getElementById("action_5").click()')
    samples=[]
    while panel.frame['t']<start+5000:
        app.processEvents();time.sleep(.03)
        samples.append(js('window.simDebug().angles.Tail'))
    assert max(samples)-min(samples)>30, samples
    print('TAIL MOTION',min(samples),max(samples),flush=True)
    panel.open_angles()
    wait(lambda:bool(js('window.simDebug().manual')))
    js('document.getElementById("a_R_Front").value=-36;document.getElementById("a_R_Front").dispatchEvent(new Event("input"));')
    assert 'SetDuty(9)' in js('document.getElementById("out_R_Front").textContent')
    print('ANGLE',js('document.getElementById("detail_R_Front").textContent'),flush=True)
    deadline=time.monotonic()+.5
    while time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    panel.web.grab().save(str(Path('build/simulation_angles_v16_3.png').resolve()))
    js('document.getElementById("copyPose").click()');wait(lambda:'SetDuty' in app.clipboard().text())
    print('PASS: autoload, real Bluetooth callback, physics, angle conversion, copy.',flush=True)
    from simulator.engine import load_sources
    sample=Path(tempfile.mkdtemp(prefix='horse-sim-edit-'))
    for name,text in load_sources('reference_projects/Dog').items():
        path=sample/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    action=sample/'src/PWM.c';original=action.read_text(encoding='utf-8')
    w.project_root=str(sample);w.open_file_path(str(action))
    editor=w.editor.editor_for(str(action));editor.setText(original.replace('(100 - duty)','(100 - duty - 1)'));editor.setModified(True)
    panel.source.setCurrentIndex(0)
    wait(lambda:panel.mappings is not None and not panel.pending_reload)
    wait(lambda:any(s['value']==8 and s['pulse_ms']==1.8 for s in panel.mappings['R_Front']['samples']))
    assert action.read_text(encoding='utf-8')==original
    editor.setModified(False)
    print('PASS: current unsaved PWM source changes measured integer mapping.',flush=True)
finally:
    panel.stop()
    wait(lambda:panel.worker is None)
    w.close();app.processEvents()
