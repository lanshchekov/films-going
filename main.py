import sys

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QApplication

from structure.MainPage import MainPage


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    # Для экранов с высоким разрешением
    if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    main_page = MainPage()
    main_page.show()

    sys.excepthook = except_hook
    sys.exit(app.exec())
