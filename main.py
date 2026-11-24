import ctypes
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from tracktube.config import APP_NAME, ICON_PATH
from tracktube.ui.main_window import MainWindow


def main():
    if sys.platform == "win32":
        # Sin esto Windows agrupa la app bajo python.exe y muestra su ícono en la barra de tareas
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"{APP_NAME}.{APP_NAME}")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
