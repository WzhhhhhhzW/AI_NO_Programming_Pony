"""Render installer artwork from the unchanged application logo and local fonts."""
from pathlib import Path
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QImage, QLinearGradient,
                        QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "installer" / "assets"
LOGO = ROOT / "assets" / "app_icon.png"


def load_fonts():
    font_directory = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for name in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf"):
        font = font_directory / name
        if font.exists():
            QFontDatabase.addApplicationFont(str(font))
    return "Microsoft YaHei" if "Microsoft YaHei" in QFontDatabase.families() else "sans-serif"


def text(painter, family, rectangle, value, size, color, bold=False):
    font = QFont(family)
    font.setPixelSize(size)
    font.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QRectF(*rectangle), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                     value)


def circuit(painter, coordinates, endpoint):
    path = QPainterPath(QPointF(*coordinates[0]))
    for point in coordinates[1:]:
        path.lineTo(QPointF(*point))
    painter.drawPath(path)
    painter.setBrush(QColor("#294754"))
    painter.drawEllipse(QPointF(*endpoint), 1.7, 1.7)
    painter.setBrush(Qt.BrushStyle.NoBrush)


def render_sidebar(logo, family):
    # Inno Setup's sidebar is 164 x 314 logical pixels; 3x keeps text crisp.
    scale = 3
    image = QImage(164 * scale, 314 * scale, QImage.Format.Format_ARGB32)
    image.fill(QColor("#101D2B"))
    painter = QPainter(image)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    painter.scale(scale, scale)

    background = QLinearGradient(0, 0, 164, 314)
    background.setColorAt(0, QColor("#101D2B"))
    background.setColorAt(1, QColor("#172C39"))
    painter.fillRect(QRectF(0, 0, 164, 314), background)

    # Restrained circuit traces stay at the edges, away from the reading area.
    painter.setPen(QPen(QColor("#294754"), 0.8))
    circuit(painter, [(132, 0), (132, 12), (148, 28), (148, 57)], (148, 57))
    circuit(painter, [(164, 15), (155, 15), (155, 67), (149, 73)], (149, 73))
    circuit(painter, [(0, 175), (7, 175), (7, 219), (13, 225)], (13, 225))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#4CCCB3"))
    painter.drawRoundedRect(QRectF(20, 22, 29, 3), 1.5, 1.5)
    painter.drawImage(QRectF(27, 37, 110, 110), logo)

    text(painter, family, (20, 156, 130, 33), "AI 导师", 25, "#F5F9FC", bold=True)
    text(painter, family, (20, 191, 130, 20), "机器马学习伙伴", 12, "#BBCCD5")

    painter.setPen(QPen(QColor("#344957"), 0.7))
    painter.drawLine(QPointF(20, 226), QPointF(144, 226))
    for y, value in ((236, "AI 辅助开发"), (254, "3D 动作仿真"), (272, "内置学习教程")):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4CCCB3"))
        painter.drawEllipse(QPointF(22, y + 7), 1.5, 1.5)
        text(painter, family, (30, y, 116, 15), value, 10, "#D6E5EB")
    text(painter, family, (20, 296, 132, 12), "RenesasHorseTutor", 8, "#92ABB8")
    painter.end()
    return image


def render_header(logo):
    image = QImage(256, 256, QImage.Format.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawImage(QRectF(16, 16, 224, 224), logo)
    painter.end()
    return image


def main():
    app = QApplication.instance() or QApplication(["render-installer-brand"])
    family = load_fonts()
    logo = QImage(str(LOGO))
    if logo.isNull():
        raise RuntimeError(f"Cannot load logo: {LOGO}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, artwork in (("wizard_sidebar.png", render_sidebar(logo, family)),
                          ("wizard_header.png", render_header(logo))):
        target = OUTPUT / name
        if not artwork.save(str(target), "PNG"):
            raise RuntimeError(f"Cannot save installer artwork: {target}")
        print(f"{name}: {artwork.width()}x{artwork.height()} ({family})")
    return app


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
