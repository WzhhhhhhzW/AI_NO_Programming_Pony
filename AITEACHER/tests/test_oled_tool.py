import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt,QPoint
from PyQt6.QtGui import QImage,QColor
from PyQt6.QtTest import QTest
from oled_tool import pack_pixels,c_source,OledToolDialog
class OledTests(unittest.TestCase):
 def test_layout(self):
  p=[[False]*2 for _ in range(9)];p[0][0]=True;p[7][0]=True;p[1][1]=True;p[8][1]=True
  self.assertEqual(pack_pixels(p),bytes([0x81,0x02,0,1]))
 def test_decode_roundtrip(self):
  p=[[(x*3+y*7)%11<4 for x in range(17)] for y in range(23)];d=pack_pixels(p)
  for y,row in enumerate(p):
   for x,on in enumerate(row):self.assertEqual(bool(d[(y//8)*17+x] & (1<<(y%8))),on)
  self.assertTrue(all(v<128 for v in d[-17:]))
 def test_bounds(self):
  p=[[False]*128 for _ in range(64)];self.assertIn('1024',c_source(p,'sprite'))
  for name,x,y in [('0bad',0,0),('sprite',1,0),('sprite',0,1)]:
   with self.assertRaises(ValueError):c_source(p,name,x,y)
 def test_ui(self):
  app=QApplication.instance() or QApplication([]);d=OledToolDialog();d.show();QTest.qWait(100)
  d.width_value.setValue(16);d.height_value.setValue(16)
  img=QImage(16,16,QImage.Format.Format_RGB32);img.fill(Qt.GlobalColor.white);img.setPixelColor(0,0,QColor('black'));d.source=img;d.regenerate()
  self.assertEqual(pack_pixels(d.canvas.pixels)[0],1)
  d.mirror.setChecked(True);self.assertTrue(d.canvas.pixels[0][15])
  d.invert.setChecked(True);self.assertFalse(d.canvas.pixels[0][15]);self.assertTrue(d.canvas.pixels[1][1])
  d.invert.setChecked(False);d.mirror.setChecked(False);d.rotate.setCurrentIndex(1);self.assertTrue(d.canvas.pixels[0][15])
  d.clear_pixels();w,h,s,ox,oy=d.canvas.geometry_values();QTest.mouseClick(d.canvas,Qt.MouseButton.LeftButton,pos=QPoint(ox+s//2,oy+s//2));self.assertTrue(d.canvas.pixels[0][0])
  QTest.mouseClick(d.canvas,Qt.MouseButton.RightButton,pos=QPoint(ox+s//2,oy+s//2));self.assertFalse(d.canvas.pixels[0][0])
  d.width_value.setValue(64);d.height_value.setValue(32);d.rotate.setCurrentIndex(0);d.mode.setCurrentIndex(1);self.assertTrue(any(any(row) for row in d.canvas.pixels))
  d.copy.click();self.assertEqual(app.clipboard().text(),d.current_code)
  QTest.qWait(100);d.grab().save('build/oled_tool_dark.png');d.apply_theme('light');QTest.qWait(100);d.grab().save('build/oled_tool_light.png');d.close()
if __name__=='__main__':unittest.main()
