import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSlider, QSpinBox, QGroupBox, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QTimer
from canvas import AutomataCanvas
from models import LifeModel, FireModel
from patterns import PATTERNS


class CellularAutomatonApp(QWidget):
    """Versión compacta y centrada del simulador de autómatas celulares."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulación Digital - Autómata Celular")
        self.resize(1000, 800)  # Tamaño de ventana equilibrado
        self.rows, self.cols, self.cell_size = 35, 50, 15
        self.model = "life"
        self.tick = 0

        self.canvas = AutomataCanvas(self.rows, self.cols, self.cell_size, self.model)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_grid)
        self.init_ui()
        self.apply_dark_theme()

    # ============================== INTERFAZ ==============================
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(15, 10, 15, 10)

        # --- Configuración del modelo ---
        model_box = QGroupBox("Configuración del modelo")
        model_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        model_layout = QHBoxLayout()
        model_layout.setContentsMargins(8, 4, 8, 4)
        model_layout.setSpacing(6)

        model_layout.addWidget(QLabel("Modelo:"))
        self.model_box = QComboBox(); self.model_box.addItems(["life", "fire"])
        self.model_box.currentTextChanged.connect(self.change_model)
        model_layout.addWidget(self.model_box)

        model_layout.addWidget(QLabel("Ancho:"))
        self.width_spin = QSpinBox(); self.width_spin.setRange(10, 100); self.width_spin.setValue(self.cols)
        model_layout.addWidget(self.width_spin)

        model_layout.addWidget(QLabel("Alto:"))
        self.height_spin = QSpinBox(); self.height_spin.setRange(10, 35); self.height_spin.setValue(self.rows)
        self.width_spin.valueChanged.connect(self.resize_grid)
        self.height_spin.valueChanged.connect(self.resize_grid)
        model_layout.addWidget(self.height_spin)

        model_layout.addWidget(QLabel("Patrón:"))
        self.pattern_box = QComboBox(); self.pattern_box.addItems(["Ninguno"] + list(PATTERNS.keys()))
        self.pattern_box.currentTextChanged.connect(self.insert_pattern)
        model_layout.addWidget(self.pattern_box)
        model_box.setLayout(model_layout)
        layout.addWidget(model_box)

        # --- Controles de simulación ---
        controls_box = QGroupBox("Controles de simulación")
        controls_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ctrl = QHBoxLayout()
        ctrl.setContentsMargins(8, 4, 8, 4)
        ctrl.setSpacing(6)
        self.play_btn = QPushButton("▶ Play")
        self.stop_btn = QPushButton("⏹ Stop")
        self.step_btn = QPushButton("⏭ Step")
        self.random_btn = QPushButton("🎲 Random")
        self.clear_btn = QPushButton("🧹 Clear")
        for btn, fn in [
            (self.play_btn, self.start), (self.stop_btn, self.stop),
            (self.step_btn, self.step), (self.random_btn, self.randomize),
            (self.clear_btn, self.clear)
        ]:
            btn.clicked.connect(fn); ctrl.addWidget(btn)
        controls_box.setLayout(ctrl)
        layout.addWidget(controls_box)

        # --- Velocidad ---
        speed_box = QGroupBox("Velocidad")
        speed_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sp = QHBoxLayout()
        sp.setContentsMargins(8, 4, 8, 4)
        sp.setSpacing(6)
        self.speed_slider = QSlider(Qt.Horizontal); self.speed_slider.setRange(1, 30); self.speed_slider.setValue(10)
        self.speed_slider.valueChanged.connect(self.change_speed)
        self.speed_label = QLabel("Ticks/segundo: 10")
        sp.addWidget(self.speed_label); sp.addWidget(self.speed_slider)
        speed_box.setLayout(sp)
        layout.addWidget(speed_box)

        # --- Separador flexible ---
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Canvas centrado ---
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas, alignment=Qt.AlignCenter)

        # --- Separador flexible ---
        layout.addItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # --- Estado ---
        self.status = QLabel("Tick: 0 | Vivos: 0 | Densidad: 0.000")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)

    # ============================== ESTILO DARK ==============================
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #f2f2f2;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }

            QGroupBox {
                background-color: #3b3b3b;
                border: 1px solid #555;
                border-radius: 6px;
                font-weight: bold;
                margin-top: 18px;       /* 🔹 deja espacio para el título */
                padding-top: 10px;      /* 🔹 evita superposición interna */
                padding-left: 6px;
                padding-right: 6px;
                padding-bottom: 4px;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 2px 6px;
                color: #ffffff;
                font-size: 9.5pt;
            }

            QLabel {
                color: #f2f2f2;
            }

            QComboBox, QSpinBox {
                background-color: #4b4b4b;
                color: #ffffff;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 2px 4px;
            }

            QComboBox::drop-down {
                border-left: 1px solid #666;
                background-color: #3b3b3b;
            }

            QSlider::groove:horizontal {
                height: 6px;
                background: #555;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background: #00bcd4;
                width: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }

            QPushButton {
                background-color: #4b4b4b;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 4px 8px;      /* 🔹 botones más pequeños */
                font-size: 9.5pt;
            }

            QPushButton:hover { background-color: #5c5c5c; }
            QPushButton:pressed { background-color: #777; }
            QPushButton[text*="Play"] { background-color: #2e7d32; }
            QPushButton[text*="Stop"] { background-color: #c62828; }
            QPushButton[text*="Clear"] { background-color: #616161; }
            QPushButton[text*="Random"] { background-color: #1565c0; }
            QPushButton[text*="Step"] { background-color: #00897b; }
        """)
        self.canvas.setStyleSheet("background-color: #eaeaea; border: 1px solid #777;")
    # ============================== LÓGICA ==============================
    def change_model(self, m): 
        self.model = m; 
        self.canvas.set_model(m); 
        self.clear()

    def change_speed(self, v):
        tps = max(1, v)
        self.timer.setInterval(int(1000 / tps))
        self.speed_label.setText(f"Ticks/segundo: {tps}")

    def resize_grid(self):
        self.rows, self.cols = self.height_spin.value(), self.width_spin.value()
        self.canvas.set_grid_shape(self.rows, self.cols)
        self.tick = 0

    def start(self):
        if not self.timer.isActive():
            tps = max(1, self.speed_slider.value())
            self.timer.setInterval(int(1000 / tps))
            self.timer.start()

    def stop(self): 
        self.timer.stop()

    def step(self): 
        self.update_grid()

    def randomize(self):
        if self.model == "life":
            self.canvas.grid = np.random.choice([0, 1], (self.rows, self.cols))
        else:
            self.canvas.grid = np.random.choice([0, 1, 2], (self.rows, self.cols), p=[0.7, 0.25, 0.05])
        self.canvas.update()
        self.tick = 0

    def clear(self):
        self.canvas.grid[:] = 0
        self.canvas.update()
        self.tick = 0
        self.status.setText("Tick: 0 | Vivos: 0 | Densidad: 0.000")

    def insert_pattern(self, name):
        """Inserta un patrón predefinido o limpia el tablero si se elige 'Ninguno'."""
        # Si el modelo no es 'life', o si selecciona 'Ninguno', limpiamos la grilla
        if self.model != "life" or name == "Ninguno":
            self.clear()
            return

        # Si selecciona un patrón válido
        self.clear()
        p = PATTERNS.get(name)
        if p is None:
            return

        # Centramos el patrón en la grilla
        r, c = p.shape
        mr, mc = self.rows // 2 - r // 2, self.cols // 2 - c // 2
        self.canvas.grid[mr:mr + r, mc:mc + c] = p
        self.canvas.update()


    def update_grid(self):
        grid = self.canvas.grid.copy()
        if self.model == "life":
            new = LifeModel.step(grid)
        else:
            new = FireModel.step(grid)
        self.canvas.grid = new
        self.canvas.update()
        self.tick += 1
        alive = int(np.sum(new > 0))
        dens = alive / (self.rows * self.cols)
        self.status.setText(f"Tick: {self.tick} | Vivos: {alive} | Densidad: {dens:.3f}")
