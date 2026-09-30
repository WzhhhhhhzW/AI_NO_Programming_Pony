import unittest
from PyQt6.QtWidgets import QApplication
from serial_debug import SerialDialog,encode_message
class FakePort:
 def __init__(self):self.opened=True;self.data=b'';self.sent=[]
 def isOpen(self):return self.opened
 def close(self):self.opened=False
 def readAll(self):return self.data
 def bytesToWrite(self):return 0
 def write(self,data):self.sent.append(data);return len(data)
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_formats(self):
  self.assertEqual(encode_message('1',False,'utf-8',''),b'1')
  self.assertEqual(encode_message('你好',False,'gbk','\r\n'),'你好\r\n'.encode('gbk'))
  self.assertEqual(encode_message('00 FF\n31',True,'ascii','\r\n'),b'\x00\xff1')
  for value in ('1','0x01','GG',''):
   with self.assertRaises(ValueError):encode_message(value,True,'ascii','')
 def test_stream_send_disconnect(self):
  d=SerialDialog();p=FakePort();d.port=p;d.update_connection_ui()
  data='小马'.encode();p.data=data[:2];d.receive_data();self.assertEqual(d.log.toPlainText(),'')
  p.data=data[2:];d.receive_data();self.assertEqual(d.log.toPlainText(),'小马');self.assertEqual(d.rx_count,len(data))
  d.rx_hex.setChecked(True);p.data=b'\x00\xff';d.receive_data();self.assertIn('00 FF',d.log.toPlainText())
  d.input.setPlainText('1');d.send_data();self.assertEqual(p.sent,[b'1'])
  d.tx_hex.setChecked(True);d.input.setPlainText('G1');d.periodic.setChecked(True);d.send_data();self.assertFalse(d.timer.isActive());self.assertEqual(len(p.sent),1)
  d.periodic.setChecked(True);d.close();self.assertFalse(p.opened);self.assertFalse(d.timer.isActive())
 def test_no_device_and_theme(self):
  d=SerialDialog();d.ports.clear();d.toggle_connection();self.assertFalse(d.port.isOpen());self.assertIn('选择串口',d.status.text())
  d.show();self.app.processEvents();d.grab().save('build/serial_dark.png');d.apply_theme('light');self.app.processEvents();d.grab().save('build/serial_light.png');d.close()
if __name__=='__main__':unittest.main()
