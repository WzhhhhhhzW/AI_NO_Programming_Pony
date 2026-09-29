"""Dog OLED bitmap conversion: vertical bytes, LSB at top, page then column."""
import re
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QImage, QPainter, QColor, QFont, QTransform
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QSpinBox, QComboBox, QCheckBox, QLineEdit, QPlainTextEdit, QFileDialog,
    QMessageBox, QApplication, QWidget, QFontComboBox, QSplitter)
from styles import dialog_stylesheet


def pack_pixels(pixels):
    height=len(pixels); width=len(pixels[0]) if height else 0
    return bytes(sum((1 << bit) for bit in range(8)
                     if page*8+bit<height and pixels[page*8+bit][x])
                 for page in range((height+7)//8) for x in range(width))


def c_source(pixels, name, x=0, y=0):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) or name.startswith('__') or name in {'auto','break','case','char','const','continue','default','do','double','else','enum','extern','float','for','goto','if','int','long','register','return','short','signed','sizeof','static','struct','switch','typedef','union','unsigned','void','volatile','while'}:
        raise ValueError('数组名请使用英文字母、数字和下划线，且不能以数字开头。')
    width=len(pixels[0]);height=len(pixels);padded=(height+7)//8*8
    if width+x>128 or padded+y>64:
        raise ValueError('图片超出 128×64 显示范围（高度按 8 像素补齐）。')
    data=pack_pixels(pixels)
    lines=['    '+', '.join(f'0x{v:02X}' for v in data[i:i+16])+',' for i in range(0,len(data),16)]
    return (f'/* {width} x {height} pixels; stored height {padded}; {len(data)} bytes.\n'
            ' * Dog OLED_ShowPicture: vertical 8 pixels, LSB top, page then column.\n'
            ' * Include oled.h before this definition. Define in ONE .c file. */\n'
            f'unsigned char {name}[{len(data)}] = {{\n'+ '\n'.join(lines)+'\n};\n\n'
            '/* Copy these calls into your display function:\n'
            'OLED_Clear();\n'
            f'OLED_ShowPicture({x}, {y}, {width}, {padded}, {name}, 1);\n'
            'OLED_Refresh();\n*/\n')


class PixelCanvas(QWidget):
    def __init__(self, changed):
        super().__init__();self.pixels=[];self.changed=changed;self.ink=True
        self.setMinimumSize(420,240)
    def geometry_values(self):
        h=len(self.pixels);w=len(self.pixels[0]) if h else 1
        scale=max(1,min((self.width()-20)//w,(self.height()-20)//max(h,1)))
        return w,h,scale,(self.width()-w*scale)//2,(self.height()-h*scale)//2
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#101a22'))
        w,h,s,ox,oy=self.geometry_values()
        for y,row in enumerate(self.pixels):
            for x,on in enumerate(row):
                p.fillRect(ox+x*s,oy+y*s,s,s,QColor('#65e6f5' if on else '#030a10'))
        if s>=7:
            p.setPen(QColor('#263746'))
            for x in range(w+1):p.drawLine(ox+x*s,oy,ox+x*s,oy+h*s)
            for y in range(h+1):p.drawLine(ox,oy+y*s,ox+w*s,oy+y*s)
    def draw_at(self,event):
        w,h,s,ox,oy=self.geometry_values();x=int((event.position().x()-ox)//s);y=int((event.position().y()-oy)//s)
        if 0<=x<w and 0<=y<h:
            self.pixels[y][x]=self.ink;self.update();self.changed()
    def mousePressEvent(self,event):
        if event.button() in (Qt.MouseButton.LeftButton,Qt.MouseButton.RightButton):
            self.ink=event.button()==Qt.MouseButton.LeftButton;self.draw_at(event)
    def mouseMoveEvent(self,event):
        if event.buttons() & (Qt.MouseButton.LeftButton|Qt.MouseButton.RightButton):self.draw_at(event)


class OledToolDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle('OLED 取模工具');self.resize(1120,800)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint,True)
        self.source=QImage();self.source_name='未选择图片';self.current_code=''
        outer=QVBoxLayout(self);intro=QLabel('适配小马标准工程 · OLED 128×64 · 纵向 8 点 / 低位在上 / 按页排列')
        outer.addWidget(intro);split=QSplitter();outer.addWidget(split,1)
        settings=QWidget();form=QFormLayout(settings);split.addWidget(settings)
        self.mode=QComboBox();self.mode.addItems(['图片取模','文字取模']);form.addRow('来源',self.mode)
        choose=QPushButton('导入图片…');choose.clicked.connect(self.load_image);form.addRow(choose)
        self.file_label=QLabel(self.source_name);self.file_label.setWordWrap(True);form.addRow(self.file_label)
        self.text=QLineEdit('小马');form.addRow('文字',self.text)
        self.font=QFontComboBox();form.addRow('字体',self.font)
        self.font_size=self.spin(8,64,24);form.addRow('字号（像素）',self.font_size)
        self.width_value=self.spin(1,128,64);self.height_value=self.spin(1,64,64)
        form.addRow('宽度',self.width_value);form.addRow('高度',self.height_value)
        self.fit=QComboBox();self.fit.addItems(['保持比例，居中留白','拉伸至目标尺寸']);form.addRow('缩放',self.fit)
        self.threshold=self.spin(0,255,128);form.addRow('黑白阈值',self.threshold)
        self.invert=QCheckBox('反色');form.addRow(self.invert)
        self.rotate=QComboBox();self.rotate.addItems(['0°','90°','180°','270°']);form.addRow('旋转',self.rotate)
        self.mirror=QCheckBox('水平镜像');form.addRow(self.mirror)
        self.name=QLineEdit('horse_bitmap');form.addRow('数组名称',self.name)
        self.x=self.spin(0,127,0);self.y=self.spin(0,63,0);form.addRow('显示位置 X',self.x);form.addRow('显示位置 Y',self.y)
        reset=QPushButton('从来源重新生成');reset.clicked.connect(self.regenerate);form.addRow(reset)
        clear=QPushButton('清空点阵');clear.clicked.connect(self.clear_pixels);form.addRow(clear)
        hint=QLabel('左键绘点，右键擦除。\n修改来源或转换参数会重新生成点阵。\n预览方向为程序坐标；竖装屏幕可旋转素材。');hint.setWordWrap(True);form.addRow(hint)
        right=QWidget();layout=QVBoxLayout(right);split.addWidget(right);split.setStretchFactor(1,1)
        self.canvas=PixelCanvas(self.update_code);layout.addWidget(self.canvas,3)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.code=QPlainTextEdit();self.code.setReadOnly(True);self.code.setFont(QFont('Consolas',10));layout.addWidget(self.code,2)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        self.copy=QPushButton('复制 C 代码');self.copy.clicked.connect(lambda:QApplication.clipboard().setText(self.current_code));buttons.addWidget(self.copy)
        self.export=QPushButton('导出 .h 文件…');self.export.clicked.connect(self.export_code);buttons.addWidget(self.export)
        save=QPushButton('导出点阵 PNG…');save.clicked.connect(self.export_image);buttons.addWidget(save)
        for box in (self.mode,self.fit,self.rotate):box.currentIndexChanged.connect(self.regenerate)
        for spin in (self.width_value,self.height_value,self.font_size,self.threshold):spin.valueChanged.connect(self.regenerate)
        for check in (self.invert,self.mirror):check.toggled.connect(self.regenerate)
        self.text.textChanged.connect(self.regenerate);self.font.currentFontChanged.connect(self.regenerate)
        self.name.textChanged.connect(self.update_code);self.x.valueChanged.connect(self.update_code);self.y.valueChanged.connect(self.update_code)
        self.apply_theme(getattr(parent,'current_theme','dark'));self.regenerate()
    @staticmethod
    def spin(low,high,value):
        spin=QSpinBox();spin.setRange(low,high);spin.setValue(value);return spin
    def apply_theme(self,theme):
        colors=('#23272e','#edf5ff','#465261') if theme=='dark' else ('#ffffff','#202020','#b8c3ce')
        bg,fg,border=colors
        self.setStyleSheet(dialog_stylesheet(theme,'unused')+f'QSpinBox {{background:{bg};color:{fg};border:1px solid {border};border-radius:4px;padding:4px;}} QSplitter::handle {{background:{border};}}')
    def load_image(self):
        path,_=QFileDialog.getOpenFileName(self,'选择图片','','图片 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)')
        if not path:return
        img=QImage(path)
        if img.isNull():QMessageBox.warning(self,'无法读取','该图片无法解码，请换用 PNG、JPG 或 BMP。');return
        self.source=img;self.source_name=path;self.file_label.setText(path)
        self.mode.setCurrentIndex(0);self.regenerate()
    def regenerate(self,*_):
        w=self.width_value.value();h=self.height_value.value();img=QImage(w,h,QImage.Format.Format_RGB32);img.fill(Qt.GlobalColor.white)
        p=QPainter(img)
        text_mode=self.mode.currentIndex()==1
        self.text.setEnabled(text_mode);self.font.setEnabled(text_mode);self.font_size.setEnabled(text_mode)
        self.fit.setEnabled(not text_mode)
        if text_mode:
            font=self.font.currentFont();font.setPixelSize(self.font_size.value());p.setFont(font);p.setPen(Qt.GlobalColor.black)
            p.drawText(QRect(0,0,w,h),Qt.AlignmentFlag.AlignCenter,self.text.text())
        elif not self.source.isNull():
            scaled=self.source.scaled(w,h,Qt.AspectRatioMode.KeepAspectRatio if self.fit.currentIndex()==0 else Qt.AspectRatioMode.IgnoreAspectRatio,Qt.TransformationMode.SmoothTransformation)
            p.drawImage((w-scaled.width())//2,(h-scaled.height())//2,scaled)
        p.end()
        if self.rotate.currentIndex():
            rotated=img.transformed(QTransform().rotate(90*self.rotate.currentIndex()))
            img.fill(Qt.GlobalColor.white);p=QPainter(img)
            rotated=rotated.scaled(w,h,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)
            p.drawImage((w-rotated.width())//2,(h-rotated.height())//2,rotated);p.end()
        if self.mirror.isChecked():img=img.mirrored(True,False)
        t=self.threshold.value();inv=self.invert.isChecked()
        self.canvas.pixels=[[(img.pixelColor(x,y).lightness()<t)^inv for x in range(w)] for y in range(h)]
        self.canvas.update();self.update_code()
    def clear_pixels(self):
        self.canvas.pixels=[[False]*self.width_value.value() for _ in range(self.height_value.value())];self.canvas.update();self.update_code()
    def update_code(self,*_):
        if not self.canvas.pixels:return
        try:
            self.current_code=c_source(self.canvas.pixels,self.name.text().strip(),self.x.value(),self.y.value())
            w=len(self.canvas.pixels[0]);h=len(self.canvas.pixels)
            self.status.setText(f'{w}×{h} 像素 · {len(pack_pixels(self.canvas.pixels))} 字节 · 高度补齐到 {(h+7)//8*8} 像素\n将数组放入一个 .c 文件，调用示例放入显示函数。文字超出画布会裁切，请以预览为准。')
        except ValueError as exc:self.current_code='';self.status.setText(str(exc))
        self.code.setPlainText(self.current_code);self.copy.setEnabled(bool(self.current_code));self.export.setEnabled(bool(self.current_code))
    def export_code(self):
        if not self.current_code:return
        path,_=QFileDialog.getSaveFileName(self,'导出 C 数组',self.name.text().strip()+'.h','C 头文件 (*.h)')
        if path:
            try:
                with open(path,'w',encoding='utf-8') as f:f.write('#pragma once\n'+self.current_code)
            except OSError as exc:QMessageBox.warning(self,'保存失败',str(exc))
    def export_image(self):
        path,_=QFileDialog.getSaveFileName(self,'导出点阵','oled_bitmap.png','PNG 图片 (*.png)')
        if not path:return
        pixels=self.canvas.pixels;img=QImage(len(pixels[0]),len(pixels),QImage.Format.Format_RGB32)
        for y,row in enumerate(pixels):
            for x,on in enumerate(row):img.setPixelColor(x,y,QColor('black' if on else 'white'))
        if not img.save(path,'PNG'):QMessageBox.warning(self,'保存失败','无法写入该文件。')
