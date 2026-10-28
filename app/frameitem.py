"""A QML item that shows a QImage as a GPU texture.

QQuickPaintedItem rasterises with QPainter on the CPU, so scaling a 1024x576
camera frame to a 1080p window cost ~30% of a core per view. Here the image is
uploaded once per frame and the GPU scales it.
"""
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickItem, QSGSimpleTextureNode, QSGTexture


class FrameItem(QQuickItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QQuickItem.ItemHasContents, True)
        self._img = None
        self._dirty = False
        self._node = None  # keep a Python reference so PySide doesn't collect it

    def set_image(self, img: QImage):
        self._img = img
        self._dirty = True
        self.update()

    def updatePaintNode(self, node, _data):
        if self._img is None or self._img.isNull() or self.window() is None:
            return node
        if node is None:
            node = QSGSimpleTextureNode()
            node.setOwnsTexture(True)
            node.setFiltering(QSGTexture.Filtering.Linear)
            self._node = node
        if self._dirty:
            node.setTexture(self.window().createTextureFromImage(self._img))
            self._dirty = False
        node.setRect(QRectF(0, 0, self.width(), self.height()))
        return node
