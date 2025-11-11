import numpy as np
from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QColor, QPen


class AutomataCanvas(QFrame):
    """Lienzo donde se dibuja y edita el autómata."""

    def __init__(self, rows, cols, cell_size=15, model="life"):
        super().__init__()
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.model = model
        self.grid = np.zeros((rows, cols), dtype=int)
        self.setFixedSize(cols * cell_size, rows * cell_size)
        self.setStyleSheet("background-color: white; border: 1px solid #aaa;")
        self.setMouseTracking(True)

    def set_model(self, model):
        self.model = model
        self.update()

    def set_grid_shape(self, rows, cols):
        new = np.zeros((rows, cols), dtype=int)
        hh = min(rows, self.rows)
        ww = min(cols, self.cols)
        new[:hh, :ww] = self.grid[:hh, :ww]
        self.grid = new
        self.rows, self.cols = rows, cols
        self.setFixedSize(cols * self.cell_size, rows * self.cell_size)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        cs = self.cell_size
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        for i in range(self.rows):
            for j in range(self.cols):
                val = int(self.grid[i, j])
                if self.model == "life":
                    color = QColor(0, 0, 0) if val == 1 else QColor(255, 255, 255)
                else:
                    if val == 0:
                        color = QColor(255, 255, 255)
                    elif val == 1:
                        color = QColor(34, 139, 34)
                    elif val == 2:
                        color = QColor(255, 69, 0)
                    else:
                        color = QColor(0, 0, 0)

                painter.fillRect(j * cs, i * cs, cs, cs, color)
                painter.setPen(QPen(QColor(220, 220, 220)))
                painter.drawRect(j * cs, i * cs, cs, cs)

    def _pos_to_cell(self, ev):
        pos = getattr(ev, "position", lambda: ev.pos())()
        x, y = pos.x(), pos.y()
        return int(y // self.cell_size), int(x // self.cell_size)

    def mousePressEvent(self, ev):
        self._toggle(ev)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.LeftButton:
            self._toggle(ev)

    def _toggle(self, ev):
        r, c = self._pos_to_cell(ev)
        if 0 <= r < self.rows and 0 <= c < self.cols:
            if self.model == "life":
                self.grid[r, c] = 1 - self.grid[r, c]
            else:
                self.grid[r, c] = (self.grid[r, c] + 1) % 3
            self.update()
