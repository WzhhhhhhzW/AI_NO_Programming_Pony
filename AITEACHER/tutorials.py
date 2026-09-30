"""Offline tutorial library: built-in PDF and video readers."""
from pathlib import Path
import sys
from loguru import logger

from PyQt6.QtCore import Qt, QPointF, QSortFilterProxyModel, QUrl
from PyQt6.QtPdf import QPdfDocument, QPdfBookmarkModel
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
                             QSpinBox, QLabel, QTreeView, QSplitter, QWidget, QLineEdit,
                             QStackedWidget, QSlider)
from styles import dialog_stylesheet

TUTORIALS = (
    '智能小马安装教程.pdf',
    '蓝牙小马-AI辅助零编程高级模式教程.pdf',
    'API的调用.pdf',
    '瑞萨入门教程1-9.pdf',
    '瑞萨入门教程10-19.pdf',
    '瑞萨入门教程oled.pdf',
)


RESOURCES = [
    {'title':'智能小马硬件安装教程','kind':'pdf','path':TUTORIALS[0]},
    {'title':'AI 辅助零编程 · 高级模式教程','kind':'pdf','path':TUTORIALS[1]},
    {'title':'AI 时代第一课 · API 的调用','kind':'pdf','path':TUTORIALS[2]},
    {'title':'瑞萨入门教程 1–9','kind':'pdf','path':TUTORIALS[3]},
    {'title':'瑞萨入门教程 10–19','kind':'pdf','path':TUTORIALS[4]},
    {'title':'OLED 专题教程','kind':'pdf','path':TUTORIALS[5]},
    {'title':'蓝牙串口操作 · 视频','kind':'video','path':'蓝牙串口操作/蓝牙串口操作教程.mp4'},
    {'title':'小马建模与 3D 打印','kind':'pdf','path':'建模与3D打印/蓝牙小马-建模及3D 打印教程 .pdf'},
]


class TutorialVideo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout=QVBoxLayout(self)
        self.screen=QVideoWidget()
        layout.addWidget(self.screen,1)
        self.player=QMediaPlayer(self)
        self.audio=QAudioOutput(self)
        self.audio.setVolume(.7)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.screen)
        bar=QHBoxLayout()
        self.play=QPushButton('播放')
        self.seek=QSlider(Qt.Orientation.Horizontal)
        self.time=QLabel('00:00 / 00:00')
        self.volume=QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0,100);self.volume.setValue(70);self.volume.setMaximumWidth(100)
        for widget in (self.play,self.seek,self.time,QLabel('音量'),self.volume):bar.addWidget(widget)
        layout.addLayout(bar)
        self.error=QLabel();self.error.setWordWrap(True);layout.addWidget(self.error)
        self.play.clicked.connect(self.toggle)
        self.seek.sliderReleased.connect(lambda:self.player.setPosition(self.seek.value()))
        self.player.durationChanged.connect(lambda n:self.seek.setRange(0,n))
        self.player.positionChanged.connect(self.update_position)
        self.player.playbackStateChanged.connect(lambda state:self.play.setText('暂停' if state==QMediaPlayer.PlaybackState.PlayingState else '播放'))
        self.player.errorOccurred.connect(lambda *_:self.error.setText('视频播放失败：'+self.player.errorString()+'。请检查软件安装文件是否完整。'))
        self.volume.valueChanged.connect(lambda n:self.audio.setVolume(n/100))

    def load(self, path):
        self.player.stop();self.error.clear();self.seek.setValue(0)
        self.player.setSource(QUrl.fromLocalFile(str(path)))

    def toggle(self):
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause()
        else:self.player.play()

    def update_position(self, ms):
        if not self.seek.isSliderDown():self.seek.setValue(ms)
        def clock(n):return f'{n//60000:02}:{n//1000%60:02}'
        self.time.setText(clock(ms)+' / '+clock(self.player.duration()))


class TutorialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('教程资料')
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        self.resize(1080, 800)
        self.positions = {}
        self.current = -1
        self.apply_theme(getattr(parent,'current_theme','dark'))
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.selector = QComboBox()
        self.selector.addItems([item['title'] for item in RESOURCES])
        self.toc_toggle = QPushButton('目录')
        self.toc_toggle.setCheckable(True)
        self.toc_toggle.setChecked(True)
        bar.addWidget(self.toc_toggle)
        bar.addWidget(self.selector, 1)
        self.previous = QPushButton('上一页')
        self.next = QPushButton('下一页')
        self.page = QSpinBox()
        self.page.setPrefix('第 ')
        self.page.setSuffix(' 页')
        self.total = QLabel()
        self.zoom = QComboBox()
        self.zoom.addItems(['适合宽度', '整页', '75%', '100%', '125%', '150%', '200%'])
        for widget in (self.previous, self.page, self.total, self.next, self.zoom):
            bar.addWidget(widget)
        layout.addLayout(bar)
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        self.document = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.bookmarks = QPdfBookmarkModel(self)
        self.bookmarks.setDocument(self.document)
        self.fallback_bookmarks=QStandardItemModel(self)
        self.filtered_bookmarks = QSortFilterProxyModel(self)
        self.filtered_bookmarks.setSourceModel(self.bookmarks)
        self.filtered_bookmarks.setRecursiveFilteringEnabled(True)
        self.filtered_bookmarks.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.filtered_bookmarks.setFilterRole(int(QPdfBookmarkModel.Role.Title))
        self.toc_panel = QWidget()
        toc_layout = QVBoxLayout(self.toc_panel)
        toc_layout.setContentsMargins(0,0,6,0)
        toc_layout.addWidget(QLabel('章节目录'))
        self.toc_search = QLineEdit()
        self.toc_search.setPlaceholderText('搜索章节标题…')
        self.toc_search.setClearButtonEnabled(True)
        toc_layout.addWidget(self.toc_search)
        self.toc = QTreeView()
        self.toc.setHeaderHidden(True)
        self.toc.setIndentation(14)
        self.toc.setModel(self.filtered_bookmarks)
        self.toc.setMinimumWidth(200)
        self.toc.setWordWrap(True)
        toc_layout.addWidget(self.toc,1)
        self.reader_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.reader_splitter.addWidget(self.toc_panel)
        self.content=QStackedWidget()
        self.content.addWidget(self.view)
        self.video=TutorialVideo(self)
        self.content.addWidget(self.video)
        self.reader_splitter.addWidget(self.content)
        self.reader_splitter.setStretchFactor(1,1)
        self.reader_splitter.setSizes([280,800])
        layout.addWidget(self.reader_splitter,1)
        self.toc_toggle.toggled.connect(self.toc_panel.setVisible)
        self.toc.clicked.connect(self.open_bookmark)
        self.toc_search.textChanged.connect(self.filter_bookmarks)
        self.selector.currentIndexChanged.connect(self.load_tutorial)
        self.page.valueChanged.connect(lambda n: self.jump(n-1))
        self.previous.clicked.connect(lambda: self.jump(self.page.value()-2))
        self.next.clicked.connect(lambda: self.jump(self.page.value()))
        self.view.pageNavigator().currentPageChanged.connect(self.update_page)
        self.zoom.currentIndexChanged.connect(self.set_zoom)
        self.load_tutorial(0)

    def apply_theme(self, theme):
        spin_style = ('QSpinBox {background:#223347;color:#edf5ff;border:1px solid #496278;'
                      'border-radius:4px;padding:5px 32px 5px 7px;min-height:24px;}' if theme == 'dark' else
                      'QSpinBox {background:white;color:#202020;border:1px solid #a0a0a0;'
                      'border-radius:4px;padding:5px 32px 5px 7px;min-height:24px;}')
        tree_style = ('QTreeView {background:#1e2732;color:#e7eef5;border:1px solid #496278;}'
                      'QTreeView::item:selected {background:#275d78;color:white;}' if theme == 'dark' else
                      'QTreeView {background:white;color:#24374b;border:1px solid #bccbd8;}'
                      'QTreeView::item:selected {background:#d9eafb;color:#17324a;}')
        self.setStyleSheet(dialog_stylesheet(theme, 'unused') + spin_style + tree_style + ('QSplitter::handle {background:#496278;}' if theme=='dark' else 'QSplitter::handle {background:#bccbd8;}'))

    def load_tutorial(self, index):
        if self.current >= 0 and RESOURCES[self.current]["kind"] == "pdf":
            self.positions[self.current] = self.view.pageNavigator().currentPage()
        self.video.player.stop()
        self.current = index
        item=RESOURCES[index]
        is_pdf=item['kind']=='pdf'
        for widget in (self.previous,self.next,self.page,self.total,self.zoom,self.toc_toggle):
            widget.setVisible(is_pdf)
        self.toc_panel.setVisible(is_pdf and self.toc_toggle.isChecked())
        self.toc_search.clear()
        self.document.close()
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        path=root/'tutorials'/item['path']
        if not is_pdf:
            self.message.hide()
            if item['kind']=='video':
                self.content.setCurrentWidget(self.video)
                self.video.load(path)
            return
        self.content.setCurrentWidget(self.view)
        result = self.document.load(str(path))
        count = self.document.pageCount()
        valid = result == QPdfDocument.Error.None_ and count > 0
        if valid and self.bookmarks.rowCount()==0:
            self.fallback_bookmarks.clear()
            for page in range(count):
                row=QStandardItem(f'第 {page+1} 页')
                row.setEditable(False)
                row.setData(f'第 {page+1} 页',int(QPdfBookmarkModel.Role.Title))
                row.setData(page,int(QPdfBookmarkModel.Role.Page))
                self.fallback_bookmarks.appendRow(row)
            self.filtered_bookmarks.setSourceModel(self.fallback_bookmarks)
        else:
            self.filtered_bookmarks.setSourceModel(self.bookmarks)
        logger.info('进阶教程加载：{}，页数={}，成功={}', item['title'], count, valid)
        self.message.setText('' if valid else '教程无法打开，请确认软件文件夹中的 tutorials 资源完整。')
        self.message.setVisible(not valid)
        self.page.blockSignals(True)
        self.page.setRange(1, max(1, count))
        self.page.blockSignals(False)
        self.total.setText(f'/ 共 {count} 页')
        self.page.setEnabled(valid)
        self.zoom.setEnabled(valid)
        self.jump(min(self.positions.get(index, 0), max(0, count-1)))
        self.update_page(self.view.pageNavigator().currentPage())

    def closeEvent(self, event):
        self.video.player.pause()
        super().closeEvent(event)

    def filter_bookmarks(self, text):
        self.filtered_bookmarks.setFilterFixedString(text)
        if text:
            self.toc.expandAll()
        else:
            self.toc.collapseAll()

    def open_bookmark(self, index):
        source = self.filtered_bookmarks.mapToSource(index)
        page = source.data(int(QPdfBookmarkModel.Role.Page))
        location = source.data(int(QPdfBookmarkModel.Role.Location))
        if page is not None and 0 <= int(page) < self.document.pageCount():
            self.view.pageNavigator().jump(int(page), location or QPointF())
            self.update_page(int(page))

    def jump(self, page):
        if self.document.pageCount():
            page = max(0, min(page, self.document.pageCount()-1))
            self.view.pageNavigator().jump(page, QPointF())
            self.update_page(page)

    def update_page(self, page):
        self.page.blockSignals(True)
        self.page.setValue(page+1)
        self.page.blockSignals(False)
        self.previous.setEnabled(page > 0)
        self.next.setEnabled(page+1 < self.document.pageCount())

    def set_zoom(self, index):
        if index < 2:
            self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth if index == 0 else QPdfView.ZoomMode.FitInView)
        else:
            self.view.setZoomMode(QPdfView.ZoomMode.Custom)
            self.view.setZoomFactor(float(self.zoom.currentText().strip('%'))/100)
