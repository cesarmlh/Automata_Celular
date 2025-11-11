import sys
from PySide6.QtWidgets import QApplication
from ui_main import CellularAutomatonApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CellularAutomatonApp()
    window.show()
    sys.exit(app.exec())
