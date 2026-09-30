"""Rasterize vector arrows so release controls use Qt's built-in PNG decoder."""
from pathlib import Path
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

assets = Path(__file__).resolve().parent.parent / 'assets'
for theme in ('dark', 'light'):
    for direction in ('up', 'down'):
        stem = f'spin_{direction}_{theme}'
        renderer = QSvgRenderer(str(assets / f'{stem}.svg'))
        assert renderer.isValid(), stem
        image = QImage(24, 16, QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        renderer.render(painter, QRectF(0, 0, 24, 16))
        painter.end()
        assert image.save(str(assets / f'{stem}.png'), 'PNG'), stem
        print(f'ARROW_PNG={stem}.png')
