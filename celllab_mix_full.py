import sys
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QSlider, QSpinBox, QFrame, QGridLayout, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QPen


# ==============================
# CLASE CANVAS DE DIBUJO
# ==============================
class AutomataCanvas(QFrame):
    def __init__(self, rows, cols, cell_size=15, model="life"):
        super().__init__()
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid = np.zeros((rows, cols), dtype=int)
        self.model = model
        self.setFixedSize(cols * cell_size, rows * cell_size)
        self.setStyleSheet("background-color: white; border: 1px solid #444;")
        self.setMouseTracking(True)

    def set_model(self, model_name: str):
        self.model = model_name
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
        try:
            pos = ev.position()
            x = pos.x(); y = pos.y()
        except Exception:
            p = ev.pos()
            x = p.x(); y = p.y()
        row = int(y // self.cell_size)
        col = int(x // self.cell_size)
        return row, col

    def mousePressEvent(self, event):
        row, col = self._pos_to_cell(event)
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if self.model == "life":
                self.grid[row, col] = 1 - int(self.grid[row, col])
            else:
                self.grid[row, col] = (int(self.grid[row, col]) + 1) % 3
            self.update()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            row, col = self._pos_to_cell(event)
            if 0 <= row < self.rows and 0 <= col < self.cols:
                if self.model == "life":
                    self.grid[row, col] = 1
                else:
                    self.grid[row, col] = 1
                self.update()


# ==============================
# CLASE PRINCIPAL
# ==============================
class CellularAutomaton(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulación Digital - Autómata Celular")
        self.rows = 35
        self.cols = 50
        self.cell_size = 15
        self.model = "life"
        self.tick = 0

        self.canvas = AutomataCanvas(self.rows, self.cols, self.cell_size, model=self.model)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_grid)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        top_bar = QHBoxLayout()

        # Modelo
        top_bar.addWidget(QLabel("Modelo:"))
        self.model_box = QComboBox()
        self.model_box.addItems(["life", "fire"])
        self.model_box.currentTextChanged.connect(self.change_model)
        top_bar.addWidget(self.model_box)

        # Tamaño
        top_bar.addWidget(QLabel("Ancho:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 200)
        self.width_spin.setValue(self.cols)
        self.width_spin.valueChanged.connect(self.resize_grid)
        top_bar.addWidget(self.width_spin)

        top_bar.addWidget(QLabel("Alto:"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 200)
        self.height_spin.setValue(self.rows)
        self.height_spin.valueChanged.connect(self.resize_grid)
        top_bar.addWidget(self.height_spin)

        # 🔹 Patrón predeterminado
        top_bar.addWidget(QLabel("Patrón:"))
        self.pattern_box = QComboBox()
        self.pattern_box.addItems(["Ninguno", "Glider", "Blinker", "Toad", "Beacon", "Pulsar"])
        self.pattern_box.currentTextChanged.connect(self.insert_pattern)
        top_bar.addWidget(self.pattern_box)

        # Botones
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self.stop)
        self.step_btn = QPushButton("⏭ Step")
        self.step_btn.clicked.connect(self.step)
        self.random_btn = QPushButton("🎲 Random")
        self.random_btn.clicked.connect(self.randomize)
        self.clear_btn = QPushButton("🧹 Clear")
        self.clear_btn.clicked.connect(self.clear)

        top_bar.addWidget(self.play_btn)
        top_bar.addWidget(self.stop_btn)
        top_bar.addWidget(self.step_btn)
        top_bar.addWidget(self.random_btn)
        top_bar.addWidget(self.clear_btn)

        # Velocidad
        self.speed_label = QLabel("Velocidad (ticks/seg):")
        top_bar.addWidget(self.speed_label)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 30)
        self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.change_speed)
        top_bar.addWidget(self.speed_slider)

        layout.addLayout(top_bar)
        layout.addWidget(self.canvas, alignment=Qt.AlignCenter)

        # Parámetros FIRE
        fire_layout = QGridLayout()
        fire_layout.addWidget(QLabel("Parámetros Fire"), 0, 0, 1, 2)

        fire_layout.addWidget(QLabel("p_growth"), 1, 0)
        self.p_growth = QDoubleSpinBox()
        self.p_growth.setRange(0, 1)
        self.p_growth.setSingleStep(0.001)
        self.p_growth.setValue(0.01)
        fire_layout.addWidget(self.p_growth, 1, 1)

        fire_layout.addWidget(QLabel("p_lightning"), 2, 0)
        self.p_lightning = QDoubleSpinBox()
        self.p_lightning.setRange(0, 1)
        self.p_lightning.setSingleStep(0.001)
        self.p_lightning.setValue(0.001)
        fire_layout.addWidget(self.p_lightning, 2, 1)

        layout.addLayout(fire_layout)

        self.status_label = QLabel("Tick: 0 | Vivos: 0 | Densidad: 0.000")
        layout.addWidget(self.status_label)

        self.stop_btn.setEnabled(False)
        init_tps = max(1, self.speed_slider.value())
        self.timer.setInterval(int(1000 / init_tps))

    # ==============================
    # FUNCIONALIDAD
    # ==============================
    def change_model(self, model):
        self.model = model
        self.canvas.set_model(model)
        self.clear()

    def change_speed(self, value):
        tps = max(1, int(value))
        self.timer.setInterval(int(1000 / tps))

    def resize_grid(self):
        self.rows = self.height_spin.value()
        self.cols = self.width_spin.value()
        self.canvas.set_grid_shape(self.rows, self.cols)
        self.tick = 0

    def start(self):
        if not self.timer.isActive():
            tps = max(1, self.speed_slider.value())
            self.timer.setInterval(int(1000 / tps))
            self.timer.start()
            self.play_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

    def stop(self):
        self.timer.stop()
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def step(self):
        self.update_grid()

    def randomize(self):
        if self.model == "life":
            self.canvas.grid = np.random.choice([0, 1], (self.rows, self.cols))
        elif self.model == "fire":
            self.canvas.grid = np.random.choice([0, 1, 2], (self.rows, self.cols), p=[0.7, 0.25, 0.05])
        self.canvas.update()
        self.tick = 0

    def clear(self):
        self.canvas.grid = np.zeros((self.rows, self.cols), dtype=int)
        self.canvas.update()
        self.tick = 0
        self.status_label.setText("Tick: 0 | Vivos: 0 | Densidad: 0.000")

    def update_grid(self):
        grid = self.canvas.grid.copy()
        if self.model == "life":
            new_grid = self.update_life(grid)
        else:
            new_grid = self.update_fire(grid)
        self.canvas.grid = new_grid
        self.canvas.update()
        self.tick += 1
        alive = np.sum(new_grid > 0)
        density = alive / (self.rows * self.cols) if (self.rows * self.cols) else 0.0
        self.status_label.setText(f"Tick: {self.tick} | Vivos: {alive} | Densidad: {density:.3f}")

    # ==============================
    # PATRONES PREDETERMINADOS
    # ==============================
    def insert_pattern(self, name):
        if self.model != "life":
            return  # solo aplica a Conway
        self.clear()
        g = self.canvas.grid
        mid_r, mid_c = self.rows // 2, self.cols // 2

        patterns = {
            "Glider": np.array([
                [0, 1, 0],
                [0, 0, 1],
                [1, 1, 1]
            ]),
            "Blinker": np.array([
                [1, 1, 1]
            ]),
            "Toad": np.array([
                [0, 1, 1, 1],
                [1, 1, 1, 0]
            ]),
            "Beacon": np.array([
                [1, 1, 0, 0],
                [1, 1, 0, 0],
                [0, 0, 1, 1],
                [0, 0, 1, 1]
            ]),
            "Pulsar": np.array([
                [0,0,1,1,1,0,0,0,1,1,1,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0],
                [1,0,0,0,0,1,0,1,0,0,0,0,1],
                [1,0,0,0,0,1,0,1,0,0,0,0,1],
                [1,0,0,0,0,1,0,1,0,0,0,0,1],
                [0,0,1,1,1,0,0,0,1,1,1,0,0],
                [0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,1,1,1,0,0,0,1,1,1,0,0],
                [1,0,0,0,0,1,0,1,0,0,0,0,1],
                [1,0,0,0,0,1,0,1,0,0,0,0,1],
                [1,0,0,0,0,1,0,1,0,0,0,0,1],
                [0,0,0,0,0,0,0,0,0,0,0,0,0],
                [0,0,1,1,1,0,0,0,1,1,1,0,0]
            ])
        }

        if name != "Ninguno" and name in patterns:
            p = patterns[name]
            pr, pc = p.shape
            start_r = mid_r - pr // 2
            start_c = mid_c - pc // 2
            g[start_r:start_r+pr, start_c:start_c+pc] = p
            self.canvas.update()

    # ==============================
    # MODELOS
    # ==============================
    def update_life(self, grid):
        new_grid = grid.copy()
        for i in range(self.rows):
            for j in range(self.cols):
                total = np.sum(grid[max(0, i - 1):min(self.rows, i + 2),
                                    max(0, j - 1):min(self.cols, j + 2)]) - grid[i, j]
                if grid[i, j] == 1 and (total < 2 or total > 3):
                    new_grid[i, j] = 0
                elif grid[i, j] == 0 and total == 3:
                    new_grid[i, j] = 1
        return new_grid

    def update_fire(self, grid):
        p_growth = float(self.p_growth.value())
        p_lightning = float(self.p_lightning.value())
        new_grid = grid.copy()
        for i in range(self.rows):
            for j in range(self.cols):
                if grid[i, j] == 2:
                    new_grid[i, j] = 0
                elif grid[i, j] == 1:
                    neighbors = grid[max(0, i - 1):min(self.rows, i + 2),
                                     max(0, j - 1):min(self.cols, j + 2)]
                    if np.any(neighbors == 2) or np.random.random() < p_lightning:
                        new_grid[i, j] = 2
                elif grid[i, j] == 0 and np.random.random() < p_growth:
                    new_grid[i, j] = 1
        return new_grid


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CellularAutomaton()
    window.show()
    sys.exit(app.exec())
