"""Nonblocking serial terminal using the bundled Qt serial backend."""
import codecs
import re
from PyQt6.QtCore import QIODevice, QTimer, QDateTime
from PyQt6.QtGui import QTextCursor
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QPlainTextEdit,QCheckBox,QSpinBox,QFileDialog,QMessageBox)
from styles import dialog_stylesheet


def encode_message(text, hex_mode, encoding, ending):
    if hex_mode:
        value=re.sub(r'\s+','',text)
        if not value or len(value)%2 or not re.fullmatch('[0-9A-Fa-f]+',value):
            raise ValueError('十六进制请输入完整字节，例如：01 A0 FF。')
        return bytes.fromhex(value)
    try:return (text+ending).encode(encoding)
    except UnicodeEncodeError as exc:raise ValueError('当前编码无法表示输入文字，请切换编码。') from exc


class SerialDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('串口调试');self.resize(980,720)
        self.port=QSerialPort(self);self.rx_count=0;self.tx_count=0
        self.decoder=codecs.getincrementaldecoder('utf-8')('replace')
        self.timer=QTimer(self);self.timer.timeout.connect(self.send_data)
        layout=QVBoxLayout(self);line=QHBoxLayout();layout.addLayout(line)
        self.ports=QComboBox();self.ports.setMinimumWidth(190)
        self.refresh=QPushButton('刷新串口');self.refresh.clicked.connect(self.refresh_ports)
        self.baud=QComboBox();self.baud.setEditable(True);self.baud.addItems(['9600','19200','38400','57600','115200','230400','460800','921600']);self.baud.setCurrentText('9600')
        self.connect_button=QPushButton('打开串口');self.connect_button.clicked.connect(self.toggle_connection)
        for w in (QLabel('串口'),self.ports,self.refresh,QLabel('波特率'),self.baud,self.connect_button):line.addWidget(w)
        line=QHBoxLayout();layout.addLayout(line)
        self.bits=QComboBox();self.bits.addItems(['8','7','6','5'])
        self.parity=QComboBox();self.parity.addItems(['无校验','奇校验','偶校验'])
        self.stop=QComboBox();self.stop.addItems(['1','2'])
        self.encoding=QComboBox();self.encoding.addItems(['UTF-8','GBK','ASCII'])
        for w in (QLabel('数据位'),self.bits,QLabel('校验'),self.parity,QLabel('停止位'),self.stop,QLabel('编码'),self.encoding):line.addWidget(w)
        self.rx_hex=QCheckBox('十六进制接收');line.addWidget(self.rx_hex)
        self.timestamp=QCheckBox('接收时间');line.addWidget(self.timestamp)
        self.log=QPlainTextEdit();self.log.setReadOnly(True);self.log.document().setMaximumBlockCount(3000);layout.addWidget(self.log,1)
        self.status=QLabel('未连接');self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();layout.addLayout(row)
        self.counts=QLabel('接收 0 B · 发送 0 B');row.addWidget(self.counts);row.addStretch()
        clear=QPushButton('清空接收');clear.clicked.connect(self.log.clear);row.addWidget(clear)
        save=QPushButton('保存接收日志…');save.clicked.connect(self.save_log);row.addWidget(save)
        self.input=QPlainTextEdit();self.input.setPlaceholderText('输入待发送内容；小马蓝牙单字符指令可选择“不追加”。');self.input.setMaximumHeight(130);layout.addWidget(self.input)
        row=QHBoxLayout();layout.addLayout(row)
        self.tx_hex=QCheckBox('十六进制发送');row.addWidget(self.tx_hex)
        self.ending=QComboBox();self.ending.addItems(['不追加','换行 LF','回车 CR','回车换行 CRLF']);row.addWidget(self.ending)
        self.periodic=QCheckBox('定时发送');row.addWidget(self.periodic)
        self.interval=QSpinBox();self.interval.setRange(100,60000);self.interval.setValue(1000);self.interval.setSuffix(' ms');row.addWidget(self.interval)
        self.send=QPushButton('发送');self.send.clicked.connect(self.send_data);row.addWidget(self.send)
        self.periodic.toggled.connect(self.set_periodic);self.interval.valueChanged.connect(lambda n:self.timer.setInterval(n))
        self.tx_hex.toggled.connect(lambda checked:self.ending.setEnabled(not checked))
        self.encoding.currentTextChanged.connect(self.reset_decoder);self.rx_hex.toggled.connect(self.reset_decoder)
        self.port.readyRead.connect(self.receive_data);self.port.bytesWritten.connect(self.bytes_written);self.port.errorOccurred.connect(self.serial_error)
        self.apply_theme(getattr(parent,'current_theme','dark'));self.refresh_ports();self.update_connection_ui()
    def apply_theme(self,theme):
        bg,fg,border=('#23272e','#edf5ff','#465261') if theme=='dark' else ('white','#202020','#b8c3ce')
        self.setStyleSheet(dialog_stylesheet(theme,'unused')+f'QSpinBox {{background:{bg};color:{fg};border:1px solid {border};padding:4px 32px 4px 7px;min-height:24px;}}')
    def reset_decoder(self,*_):
        self.decoder=codecs.getincrementaldecoder(self.encoding.currentText().lower())('replace')
    def refresh_ports(self):
        selected=self.ports.currentData();self.ports.clear()
        for info in QSerialPortInfo.availablePorts():self.ports.addItem(f'{info.portName()} · {info.description()}',info.portName())
        index=self.ports.findData(selected)
        if index>=0:self.ports.setCurrentIndex(index)
        if self.ports.count()==0:self.status.setText('未检测到串口，请连接设备后刷新。')
    def update_connection_ui(self):
        opened=self.port.isOpen()
        for w in (self.ports,self.refresh,self.baud,self.bits,self.parity,self.stop):w.setEnabled(not opened)
        self.connect_button.setText('关闭串口' if opened else '打开串口');self.send.setEnabled(opened);self.periodic.setEnabled(opened)
    def toggle_connection(self):
        if self.port.isOpen():self.disconnect_port();return
        if not self.ports.currentData():self.status.setText('请先连接设备并选择串口。');return
        try:
            baud=int(self.baud.currentText())
            if not 1<=baud<=4000000:raise ValueError()
        except ValueError:self.status.setText('波特率请输入 1–4000000 范围内的整数。');return
        self.port.setPortName(self.ports.currentData())
        results=[self.port.setBaudRate(baud),self.port.setDataBits(QSerialPort.DataBits(int(self.bits.currentText()))),
                 self.port.setParity([QSerialPort.Parity.NoParity,QSerialPort.Parity.OddParity,QSerialPort.Parity.EvenParity][self.parity.currentIndex()]),
                 self.port.setStopBits(QSerialPort.StopBits.OneStop if self.stop.currentIndex()==0 else QSerialPort.StopBits.TwoStop),
                 self.port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)]
        if not all(results):self.status.setText('串口参数不受支持，请检查设置。');return
        if not self.port.open(QIODevice.OpenModeFlag.ReadWrite):self.status.setText('打开失败：'+self.port.errorString());return
        self.reset_decoder();self.status.setText(f'已连接 {self.port.portName()} · {baud} 波特');self.update_connection_ui()
    def disconnect_port(self):
        self.periodic.setChecked(False);self.timer.stop()
        if self.port.isOpen():self.port.close()
        self.update_connection_ui();self.status.setText('串口已关闭')
    def serial_error(self,error):
        if error in (QSerialPort.SerialPortError.NoError,QSerialPort.SerialPortError.NotOpenError):return
        message=self.port.errorString()
        if self.port.isOpen():self.disconnect_port()
        self.status.setText('串口错误：'+message)
    def set_periodic(self,on):
        if on and self.port.isOpen():self.timer.start(self.interval.value())
        else:self.timer.stop()
    def send_data(self):
        if not self.port.isOpen():return
        try:
            payload=encode_message(self.input.toPlainText(),self.tx_hex.isChecked(),self.encoding.currentText().lower(),['','\n','\r','\r\n'][self.ending.currentIndex()])
            if not payload:raise ValueError('请输入待发送内容。')
            if len(payload)>65536:raise ValueError('单次发送最多 64 KB。')
            if self.port.bytesToWrite()+len(payload)>65536:raise ValueError('发送缓冲区忙，请降低发送频率。')
            written=self.port.write(payload)
            if written!=len(payload):raise ValueError('发送未完整入队：'+self.port.errorString())
            self.status.setText(f'已提交 {len(payload)} 字节发送')
        except ValueError as exc:self.periodic.setChecked(False);self.status.setText(str(exc))
    def bytes_written(self,count):self.tx_count+=count;self.update_counts()
    def update_counts(self):self.counts.setText(f'接收 {self.rx_count} B · 发送 {self.tx_count} B')
    def receive_data(self):
        data=bytes(self.port.readAll());self.rx_count+=len(data);self.update_counts()
        text=data.hex(' ').upper()+' ' if self.rx_hex.isChecked() else self.decoder.decode(data)
        if not text:return
        if self.timestamp.isChecked():text='\n['+QDateTime.currentDateTime().toString('HH:mm:ss.zzz')+'] '+text
        cursor=self.log.textCursor();cursor.movePosition(QTextCursor.MoveOperation.End);cursor.insertText(text)
        # Also bound a continuous stream without newline characters.
        if self.log.document().characterCount()>250000:
            cut=QTextCursor(self.log.document());cut.setPosition(0);cut.setPosition(self.log.document().characterCount()-200000,QTextCursor.MoveMode.KeepAnchor);cut.removeSelectedText()
        self.log.setTextCursor(cursor);self.log.ensureCursorVisible()
    def save_log(self):
        path,_=QFileDialog.getSaveFileName(self,'保存接收日志','serial_log.txt','文本文件 (*.txt)')
        if path:
            try:
                with open(path,'w',encoding='utf-8') as f:f.write(self.log.toPlainText())
            except OSError as exc:QMessageBox.warning(self,'保存失败',str(exc))
    def closeEvent(self,event):self.disconnect_port();super().closeEvent(event)
