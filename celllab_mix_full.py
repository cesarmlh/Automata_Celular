    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CellLab Mix — Full (corregido y visible)
----------------------------------------
- PySide6 GUI con canvas (fondo BLANCO, celdas visibles)
- Modelos: Game of Life (life) y Forest Fire (fire)
- Controles: Play, Step, Random, Clear, Velocidad, tamaño de grilla
- CRUD de Presets (SQLite) y guardado de Runs con estadísticas
- Edición con el mouse (Life: 0/1; Fire: 0→1→2→0)
- Código documentado

Requisitos:
    pip install PySide6 numpy
Ejecución:
    python celllab_mix_full.py
"""
import json, sqlite3
from dataclasses import dataclass
from typing import Tuple

import numpy as np
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLabel, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QSlider, QHBoxLayout, QVBoxLayout, QGridLayout,
    QListWidget, QLineEdit, QMessageBox, QGroupBox
)

DB_FILE = "celllab.db"

# ---------------------------- Persistencia ----------------------------
def db_init():
    """Crea tablas si no existen (SQLite)."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS preset(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        model TEXT NOT NULL,             -- 'life' | 'fire'
        width INTEGER NOT NULL,
        height INTEGER NOT NULL,
        params_json TEXT NOT NULL,       -- {"p_growth":..., "p_lightning":...}
        grid_rle TEXT NOT NULL,          -- RLE del grid
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS run(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        model TEXT NOT NULL,
        params_json TEXT NOT NULL,
        ticks INTEGER NOT NULL,
        stats_summary_json TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """)
    con.commit(); con.close()

def rle_encode(arr: np.ndarray) -> str:
    """Codifica array 2D en RLE 'valor:count;...' para guardar presets compactos."""
    flat = arr.flatten()
    if flat.size == 0: return ""
    out = []
    last = flat[0]; count = 1
    for v in flat[1:]:
        if v == last:
            count += 1
        else:
            out.append(f"{int(last)}:{count}")
            last = v; count = 1
    out.append(f"{int(last)}:{count}")
    return ";".join(out)

def rle_decode(s: str, shape: Tuple[int,int]) -> np.ndarray:
    """Decodifica RLE al shape dado."""
    if not s: return np.zeros(shape, dtype=np.int8)
    vals = []
    for token in s.split(";"):
        v, c = token.split(":")
        vals.extend([int(v)]*int(c))
    arr = np.array(vals, dtype=np.int8)
    return arr.reshape(shape)

# ---------------------------- Estadísticas ----------------------------
@dataclass
class LifeStats:
    alive:int=0; births:int=0; deaths:int=0; density:float=0.0

@dataclass
class FireStats:
    empty:int=0; trees:int=0; burning:int=0; burned_total:int=0
    forest_pct:float=0.0; burning_pct:float=0.0

# ---------------------------- Simuladores ----------------------------
class GameOfLife:
    """Conway's Game of Life (0 muerto, 1 vivo)."""
    def __init__(self, h:int, w:int):
        self.h, self.w = h, w
        self.grid = np.zeros((h,w), dtype=np.int8)

    def randomize(self, p=0.35):
        """Siembra células vivas con probabilidad p (por defecto 35% para que se vea)."""
        self.grid = (np.random.rand(self.h, self.w) < p).astype(np.int8)

    def step(self) -> LifeStats:
        """Un tick de evolución del autómata y devuelve estadísticas del estado nuevo."""
        g = self.grid
        # Conteo de vecinos toroidal (suma de desplazamientos)
        n = sum(np.roll(np.roll(g, di, axis=0), dj, axis=1)
                for di in (-1,0,1) for dj in (-1,0,1) if not (di==0 and dj==0))
        births = int(((g==0) & (n==3)).sum())
        deaths = int(((g==1) & ~((n==2)|(n==3))).sum())
        newg = (((g==1) & ((n==2)|(n==3))) | ((g==0) & (n==3))).astype(np.int8)
        self.grid = newg
        alive = int(newg.sum())
        density = alive/(self.h*self.w)
        return LifeStats(alive=alive, births=births, deaths=deaths, density=float(density))

class ForestFire:
    """Modelo de incendios: 0=vacío, 1=árbol, 2=fuego (probabilístico)."""
    EMPTY, TREE, FIRE = 0,1,2
    def __init__(self, h:int, w:int, p_growth=0.01, p_lightning=0.001):
        self.h, self.w = h, w
        self.p_growth = p_growth
        self.p_lightning = p_lightning
        self.grid = np.zeros((h,w), dtype=np.int8)
        self.burned_total = 0

    def randomize(self, tree_density=0.65, fire_density=0.01):
        """Bosque denso y 1% de fuego inicial para que se note la dinámica."""
        r = np.random.rand(self.h, self.w)
        g = np.zeros((self.h, self.w), dtype=np.int8)
        g[r < tree_density] = self.TREE
        if fire_density > 0.0:
            fmask = np.random.rand(self.h, self.w) < fire_density
            g[fmask] = self.FIRE
        self.grid = g

    def step(self) -> FireStats:
        """Un tick de propagación de fuego/crecimiento con estadísticas básicas."""
        g = self.grid
        neighbor_fire = np.zeros_like(g, dtype=bool)
        for di in (-1,0,1):
            for dj in (-1,0,1):
                if di==0 and dj==0: continue
                neighbor_fire |= (np.roll(np.roll(g, di, axis=0), dj, axis=1) == self.FIRE)

        newg = np.copy(g)
        # Fuego -> vacío
        newg[g==self.FIRE] = self.EMPTY
        # Árbol -> fuego por vecinos o rayos
        trees = (g==self.TREE)
        lightning = (np.random.rand(self.h, self.w) < self.p_lightning)
        to_fire = trees & (neighbor_fire | lightning)
        newg[to_fire] = self.FIRE
        # Vacío -> árbol
        empty = (g==self.EMPTY)
        grow = (np.random.rand(self.h, self.w) < self.p_growth)
        newg[empty & grow] = self.TREE

        # Stats
        burning = int((newg==self.FIRE).sum())
        trees_now = int((newg==self.TREE).sum())
        empty_now = int((newg==self.EMPTY).sum())
        self.burned_total += int(to_fire.sum())
        self.grid = newg
        total = self.h*self.w
        return FireStats(
            empty=empty_now, trees=trees_now, burning=burning,
            burned_total=self.burned_total,
            forest_pct=trees_now/total, burning_pct=burning/total
        )

# ---------------------------- Lienzo ----------------------------
class GridCanvas(QWidget):
    """Canvas que dibuja la grilla y permite pintar con el mouse."""
    def __init__(self, cell_size=20):
        super().__init__()
        self.cell_size = cell_size
        self.model_name = "life"
        self._grid_ref = None

    def set_grid(self, grid: np.ndarray, model_name: str):
        self._grid_ref = grid
        self.model_name = model_name
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        if self._grid_ref is None:
            return QSize(800, 600)
        h, w = self._grid_ref.shape
        return QSize(self.cell_size*w, self.cell_size*h)

    def minimumSizeHint(self):
        return QSize(320, 240)

    def paintEvent(self, _):
        if self._grid_ref is None: return
        painter = QPainter(self)
        h, w = self._grid_ref.shape
        cs = self.cell_size

        # Fondo BLANCO
        painter.fillRect(self.rect(), Qt.white)

        # Celdas
        for i in range(h):
            for j in range(w):
                v = int(self._grid_ref[i, j])
                if self.model_name == "life":
                    if v == 1:
                        painter.fillRect(j*cs, i*cs, cs, cs, Qt.black)  # negro visible
                else:
                    if v == 1:
                        painter.fillRect(j*cs, i*cs, cs, cs, QColor(0, 180, 0))  # verde
                    elif v == 2:
                        painter.fillRect(j*cs, i*cs, cs, cs, QColor(255, 90, 0))  # naranja/rojo

        # Rejilla gris clara
        painter.setPen(QColor(210, 210, 210))
        for x in range(0, w*cs, cs):
            painter.drawLine(x, 0, x, h*cs)
        for y in range(0, h*cs, cs):
            painter.drawLine(0, y, w*cs, y)

    def mousePressEvent(self, ev):
        self._toggle_cell(ev)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.LeftButton:
            self._toggle_cell(ev)

    def _toggle_cell(self, ev):
        if self._grid_ref is None: return
        cs = self.cell_size
        pos = ev.position()
        j = int(pos.x() // cs)
        i = int(pos.y() // cs)
        h, w = self._grid_ref.shape
        if 0 <= i < h and 0 <= j < w:
            if self.model_name == "life":
                self._grid_ref[i, j] = 1 - self._grid_ref[i, j]
            else:
                # 0->1->2->0
                self._grid_ref[i, j] = (self._grid_ref[i, j] + 1) % 3
            self.update()

# ---------------------------- Ventana Principal ----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CellLab Mix — Full (Corregido)")
        self.resize(1280, 760)

        # Estado general
        self.model_name = "life"
        self.grid_w = 50
        self.grid_h = 35
        self.life = GameOfLife(self.grid_h, self.grid_w)
        self.fire = ForestFire(self.grid_h, self.grid_w)
        self.tick = 0

        # Canvas + timer
        self.canvas = GridCanvas(cell_size=20)
        self.canvas.set_grid(self.life.grid, "life")
        self.timer = QTimer(self); self.timer.setInterval(100)
        self.timer.timeout.connect(self.on_step)

        # ---------- Controles ----------
        self.btn_play   = QPushButton("▶ Play")
        self.btn_step   = QPushButton("⏭ Step")
        self.btn_random = QPushButton("🎲 Random")
        self.btn_clear  = QPushButton("🧹 Clear")
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_step.clicked.connect(self.on_step)
        self.btn_random.clicked.connect(self.on_random)
        self.btn_clear.clicked.connect(self.on_clear)

        self.speed_slider = QSlider(Qt.Horizontal); self.speed_slider.setRange(1, 60); self.speed_slider.setValue(10)
        self.speed_label  = QLabel("Velocidad: 10 tps")
        self.speed_slider.valueChanged.connect(self.on_speed_change)

        self.model_combo = QComboBox(); self.model_combo.addItems(["life", "fire"])
        self.model_combo.currentTextChanged.connect(self.on_model_change)
        self.w_spin = QSpinBox(); self.w_spin.setRange(10, 200); self.w_spin.setValue(self.grid_w)
        self.h_spin = QSpinBox(); self.h_spin.setRange(10, 200); self.h_spin.setValue(self.grid_h)
        self.w_spin.valueChanged.connect(self.on_resize_grid)
        self.h_spin.valueChanged.connect(self.on_resize_grid)

        fire_box = QGroupBox("Parámetros Fire")
        self.p_growth = QDoubleSpinBox(); self.p_growth.setRange(0.0, 1.0); self.p_growth.setDecimals(3); self.p_growth.setSingleStep(0.001); self.p_growth.setValue(0.010)
        self.p_light  = QDoubleSpinBox(); self.p_light.setRange(0.0, 1.0);  self.p_light.setDecimals(3);  self.p_light.setSingleStep(0.001);  self.p_light.setValue(0.001)
        self.p_growth.valueChanged.connect(self.on_fire_params)
        self.p_light.valueChanged.connect(self.on_fire_params)
        fire_l = QGridLayout()
        fire_l.addWidget(QLabel("p_growth"), 0,0); fire_l.addWidget(self.p_growth,0,1)
        fire_l.addWidget(QLabel("p_lightning"),1,0); fire_l.addWidget(self.p_light, 1,1)
        fire_box.setLayout(fire_l)

        # CRUD Presets
        self.preset_list = QListWidget()
        self.preset_name = QLineEdit(); self.preset_name.setPlaceholderText("Nombre del preset...")
        self.btn_save_preset   = QPushButton("Guardar/Actualizar")
        self.btn_delete_preset = QPushButton("Eliminar")
        self.btn_load_preset   = QPushButton("Cargar")
        self.btn_save_preset.clicked.connect(self.save_preset)
        self.btn_delete_preset.clicked.connect(self.delete_preset)
        self.btn_load_preset.clicked.connect(self.load_preset)
        self.refresh_presets()

        # Runs y Stats
        self.run_name = QLineEdit(); self.run_name.setPlaceholderText("Nombre del run (opcional)")
        self.btn_save_run = QPushButton("Guardar Run")
        self.btn_save_run.clicked.connect(self.save_run)
        self.tick_label  = QLabel("Tick: 0")
        self.stats_label = QLabel("Stats: -")

        # ---------- Layouts ----------
        # Barra superior
        top = QGridLayout()
        r = 0
        top.addWidget(QLabel("Modelo:"), r,0); top.addWidget(self.model_combo, r,1)
        top.addWidget(QLabel("Ancho:"),  r,2); top.addWidget(self.w_spin,     r,3)
        top.addWidget(QLabel("Alto:"),   r,4); top.addWidget(self.h_spin,     r,5); r+=1
        top.addWidget(self.btn_play, r,0); top.addWidget(self.btn_step, r,1)
        top.addWidget(self.btn_random, r,2); top.addWidget(self.btn_clear, r,3)
        top.addWidget(QLabel("Velocidad (ticks/seg):"), r,4); top.addWidget(self.speed_slider, r,5); r+=1
        top.addWidget(self.speed_label, r,0,1,6); r+=1

        # Columna derecha (parámetros + presets + run + stats)
        right = QVBoxLayout()
        right.addWidget(fire_box)
        right.addWidget(QLabel("Presets"))
        right.addWidget(self.preset_list, stretch=1)
        preset_row1 = QHBoxLayout(); preset_row1.addWidget(self.preset_name); preset_row1.addWidget(self.btn_save_preset)
        preset_row2 = QHBoxLayout(); preset_row2.addWidget(self.btn_load_preset); preset_row2.addWidget(self.btn_delete_preset)
        right.addLayout(preset_row1); right.addLayout(preset_row2)
        right.addWidget(QLabel("Run"))
        right.addWidget(self.run_name)
        right.addWidget(self.btn_save_run)
        right.addWidget(self.tick_label)
        right.addWidget(self.stats_label)

        # Root
        left = QVBoxLayout()
        left.addLayout(top)
        left.addWidget(self.canvas, stretch=1)

        root = QHBoxLayout()
        root.addLayout(left, stretch=3)
        root.addLayout(right, stretch=2)

        container = QWidget(); container.setLayout(root)
        self.setCentralWidget(container)

        # Estado inicial visible
        self.update_stats_now()

    # -------------------- Callbacks --------------------
    def on_speed_change(self, val:int):
        self.speed_label.setText(f"Velocidad: {val} tps")
        if self.timer.isActive():
            self.timer.setInterval(int(1000/max(1, val)))

    def toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("▶ Play")
        else:
            tps = max(1, self.speed_slider.value())
            self.timer.setInterval(int(1000/tps))
            self.timer.start()
            self.btn_play.setText("⏸ Pause")

    def on_step(self):
        self.tick += 1
        if self.model_name == "life":
            st = self.life.step()
            self.stats_label.setText(
                f"Vivos={st.alive}  Nac={st.births}  Muertes={st.deaths}  Densidad={st.density:.3f}"
            )
        else:
            st = self.fire.step()
            self.stats_label.setText(
                f"Vacíos={st.empty}  Árboles={st.trees}  Fuego={st.burning}  QuemadoAcum={st.burned_total}  Bosque%={st.forest_pct:.3f}  Fuego%={st.burning_pct:.3f}"
            )
        self.tick_label.setText(f"Tick: {self.tick}")
        self.canvas.update()

    def on_clear(self):
        """Limpia grilla y resetea play/tick (corregido)."""
        self.timer.stop()
        self.btn_play.setText("▶ Play")
        self.tick = 0
        if self.model_name == "life":
            self.life.grid[:] = 0
        else:
            self.fire.grid[:] = 0
            self.fire.burned_total = 0
        self.tick_label.setText("Tick: 0")
        self.update_stats_now()
        self.canvas.update()

    def on_random(self):
        """Genera un estado aleatorio visible (Life 35% vivas; Fire 65% árboles + 1% fuego)."""
        self.tick = 0
        if self.model_name == "life":
            self.life.randomize(p=0.35)
        else:
            self.fire.randomize(tree_density=0.65, fire_density=0.01)
            self.fire.burned_total = 0
        self.tick_label.setText("Tick: 0")
        self.update_stats_now()
        self.canvas.update()

    def on_model_change(self, name: str):
        self.model_name = name
        if name == "life":
            self.canvas.set_grid(self.life.grid, "life")
        else:
            self.canvas.set_grid(self.fire.grid, "fire")
        self.tick = 0
        self.tick_label.setText("Tick: 0")
        self.update_stats_now()
        self.canvas.update()

    def on_resize_grid(self, _=None):
        """Redimensiona la grilla conservando lo que quepa del estado actual."""
        w = self.w_spin.value(); h = self.h_spin.value()
        self.grid_w, self.grid_h = w, h
        if self.model_name == "life":
            newg = np.zeros((h,w), dtype=np.int8)
            hh, ww = self.life.grid.shape
            newg[:min(h,hh), :min(w,ww)] = self.life.grid[:min(h,hh), :min(w,ww)]
            self.life = GameOfLife(h, w); self.life.grid = newg
            self.canvas.set_grid(self.life.grid, "life")
        else:
            newg = np.zeros((h,w), dtype=np.int8)
            hh, ww = self.fire.grid.shape
            newg[:min(h,hh), :min(w,ww)] = self.fire.grid[:min(h,hh), :min(w,ww)]
            self.fire = ForestFire(h, w, self.p_growth.value(), self.p_light.value()); self.fire.grid = newg
            self.canvas.set_grid(self.fire.grid, "fire")
        self.tick = 0
        self.tick_label.setText("Tick: 0")
        self.update_stats_now()
        self.canvas.update()

    def on_fire_params(self, _=None):
        if self.model_name == "fire":
            self.fire.p_growth = self.p_growth.value()
            self.fire.p_lightning = self.p_light.value()

    # -------------------- Stats actuales --------------------
    def update_stats_now(self):
        if self.model_name == "life":
            alive = int(self.life.grid.sum())
            density = alive/(self.grid_w*self.grid_h) if (self.grid_w*self.grid_h) else 0.0
            self.stats_label.setText(f"Vivos={alive}  Densidad={density:.3f}")
        else:
            g = self.fire.grid
            empty  = int((g==ForestFire.EMPTY).sum())
            trees  = int((g==ForestFire.TREE).sum())
            burn   = int((g==ForestFire.FIRE).sum())
            total  = g.size if g.size else 1
            self.stats_label.setText(f"Vacíos={empty} Árboles={trees} Fuego={burn} Bosque%={trees/total:.3f}")

    # -------------------- CRUD Presets --------------------
    def refresh_presets(self):
        db_init()
        con = sqlite3.connect(DB_FILE); cur = con.cursor()
        cur.execute("SELECT id,name,model,width,height FROM preset ORDER BY name ASC")
        rows = cur.fetchall(); con.close()
        self.preset_list.clear()
        for pid, name, model, w, h in rows:
            self.preset_list.addItem(f"{pid} | {name} | {model} {w}x{h}")

    def _current_grid(self) -> np.ndarray:
        return self.life.grid if self.model_name == "life" else self.fire.grid

    def save_preset(self):
        name = self.preset_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Preset", "Ponle un nombre al preset."); return
        grid = self._current_grid()
        params = {}
        if self.model_name == "fire":
            params = {"p_growth": self.p_growth.value(), "p_lightning": self.p_light.value()}
        rle = rle_encode(grid)
        con = sqlite3.connect(DB_FILE); cur = con.cursor()
        # UPSERT por nombre
        cur.execute("SELECT id FROM preset WHERE name=?", (name,))
        row = cur.fetchone()
        if row:
            cur.execute("""UPDATE preset SET model=?, width=?, height=?, params_json=?, grid_rle=? WHERE id=?""",
                        (self.model_name, grid.shape[1], grid.shape[0], json.dumps(params), rle, row[0]))
        else:
            cur.execute("""INSERT INTO preset(name,model,width,height,params_json,grid_rle) VALUES(?,?,?,?,?,?)""",
                        (name, self.model_name, grid.shape[1], grid.shape[0], json.dumps(params), rle))
        con.commit(); con.close()
        self.refresh_presets()
        QMessageBox.information(self,"Preset","Preset guardado/actualizado.")

    def delete_preset(self):
        item = self.preset_list.currentItem()
        if not item:
            QMessageBox.warning(self,"Preset","Selecciona un preset en la lista."); return
        pid = int(item.text().split("|")[0].strip())
        con = sqlite3.connect(DB_FILE); cur = con.cursor()
        cur.execute("DELETE FROM preset WHERE id=?", (pid,))
        con.commit(); con.close()
        self.refresh_presets()

    def load_preset(self):
        item = self.preset_list.currentItem()
        if not item:
            QMessageBox.warning(self,"Preset","Selecciona un preset en la lista."); return
        pid = int(item.text().split("|")[0].strip())
        con = sqlite3.connect(DB_FILE); cur = con.cursor()
        cur.execute("SELECT name,model,width,height,params_json,grid_rle FROM preset WHERE id=?", (pid,))
        row = cur.fetchone(); con.close()
        if not row: return
        name, model, w, h, params_json, grid_rle = row
        self.model_combo.setCurrentText(model)
        self.w_spin.setValue(w); self.h_spin.setValue(h)
        grid = rle_decode(grid_rle, (h, w))
        if model == "life":
            self.life = GameOfLife(h, w); self.life.grid = grid
            self.canvas.set_grid(self.life.grid, "life")
        else:
            params = json.loads(params_json)
            self.fire = ForestFire(h, w, params.get("p_growth",0.01), params.get("p_lightning",0.001))
            self.fire.grid = grid
            self.p_growth.setValue(self.fire.p_growth)
            self.p_light.setValue(self.fire.p_lightning)
            self.canvas.set_grid(self.fire.grid, "fire")
        self.tick = 0
        self.tick_label.setText("Tick: 0")
        self.update_stats_now()
        self.preset_name.setText(name)

    # -------------------- Guardar Run --------------------
    def save_run(self):
        name = self.run_name.text().strip() or None
        if self.model_name == "life":
            alive = int(self.life.grid.sum())
            params = {}
            stats = {"alive": alive, "density": alive/(self.grid_w*self.grid_h)}
        else:
            g = self.fire.grid
            stats = {
                "empty": int((g==ForestFire.EMPTY).sum()),
                "trees": int((g==ForestFire.TREE).sum()),
                "burning": int((g==ForestFire.FIRE).sum()),
                "burned_total": int(self.fire.burned_total),
            }
            params = {"p_growth": self.fire.p_growth, "p_lightning": self.fire.p_lightning}
        con = sqlite3.connect(DB_FILE); cur = con.cursor()
        cur.execute("""INSERT INTO run(name,model,params_json,ticks,stats_summary_json)
                       VALUES(?,?,?,?,?)""",
                    (name, self.model_name, json.dumps(params), self.tick, json.dumps(stats)))
        con.commit(); con.close()
        QMessageBox.information(self,"Run","Run guardado en la base de datos.")

# ---------------------------- main ----------------------------
def main():
    db_init()
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()

if __name__ == "__main__":
    main()
