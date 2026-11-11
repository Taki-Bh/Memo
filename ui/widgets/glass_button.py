"""
GlassButton
===========

A QPushButton subclass used for every button in the app (sidebar
utilities, composer send/attach/tools, suggestion cards, etc).

It adds a short, subtle "lift" animation on hover/press via a
QGraphicsOpacityEffect-free approach: we animate a custom property
(`hoverProgress`) that the QSS/paintEvent can react to, keeping the
actual visual language (glass / neumorphic look) entirely in QSS so
it stays editable from Qt Designer and styles/theme.qss.

Safe to promote in Qt Designer:
    base class   -> QPushButton
    promoted to  -> GlassButton
    header file  -> widgets.glass_button
"""
from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QPushButton


class GlassButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_progress = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)

        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    # -- animated property, exposed so QSS/paint code (or Designer's
    #    dynamic-property tooling) can react to it -----------------
    def getHoverProgress(self):
        return self._hover_progress

    def setHoverProgress(self, value):
        self._hover_progress = value
        self.update()

    hoverProgress = Property(float, getHoverProgress, setHoverProgress)

    def enterEvent(self, event):
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animate_to(0.0)
        super().leaveEvent(event)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._hover_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    # -- subtle glow overlay driven by hoverProgress, layered on top
    #    of whatever QSS already paints (background/border/text) so
    #    the effect stays purely additive and non-destructive --------
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._hover_progress <= 0.0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        radius = min(self.height() / 2, 18)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), radius, radius)
        glow = QColor(92, 200, 255)
        glow.setAlphaF(0.16 * self._hover_progress)
        pen = QPen(glow, 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
