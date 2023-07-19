import os
from pathlib import Path

import qdarkstyle
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QTextEdit, QPushButton, QDialog
from PyQt5.QtWidgets import (
    QFileDialog, QCheckBox, QProgressBar
)
from loguru import logger

from dow_stickers import main_download_stickers
from main import update_db, download_new_arts_in_comp
from utils import enum_printers

path_root = Path(__file__).resolve().parent


class CustomDialog(QDialog):
    def __init__(self, parent=None):
        super(CustomDialog, self).__init__(parent)
        self.setWindowTitle("Новые артикулы")

        # Создаем текстовое поле для отображения списка артикулов
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)

        # Кнопка для закрытия диалогового окна
        self.close_button = QPushButton("Закрыть", self)
        self.close_button.clicked.connect(self.close)

        # Размещаем элементы на вертикальном слое
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        layout.addWidget(self.close_button)
        self.setLayout(layout)

    def set_text(self, text):
        self.text_edit.setPlainText(text)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(660, 685)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton.setFont(font)
        self.pushButton.setObjectName("pushButton")
        self.horizontalLayout.addWidget(self.pushButton)
        self.pushButton_2 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setObjectName("pushButton_2")
        self.horizontalLayout.addWidget(self.pushButton_2)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout_2.addWidget(self.lineEdit)
        self.pushButton_3 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_3.setFont(font)
        self.pushButton_3.setObjectName("pushButton_3")
        self.horizontalLayout_2.addWidget(self.pushButton_3)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")

        self.verticalLayout.addLayout(self.gridLayout)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.pushButton_4 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setObjectName("pushButton_4")
        self.horizontalLayout_3.addWidget(self.pushButton_4)
        self.pushButton_5 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_5.setFont(font)
        self.pushButton_5.setObjectName("pushButton_5")
        self.horizontalLayout_3.addWidget(self.pushButton_5)
        self.pushButton_6 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_6.setFont(font)
        self.pushButton_6.setObjectName("pushButton_6")
        self.horizontalLayout_3.addWidget(self.pushButton_6)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.listView = QtWidgets.QListView(self.centralwidget)
        self.listView.setObjectName("listView")
        self.verticalLayout.addWidget(self.listView)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        # Создаем второй статус бар
        self.second_statusbar = QtWidgets.QStatusBar(MainWindow)
        self.second_statusbar.setObjectName("second_statusbar")

        # Создаем первый QDockWidget для первого статус бара
        self.dock_widget_1 = QtWidgets.QDockWidget("", MainWindow)
        self.dock_widget_1.setObjectName("dock_widget_1")
        self.dock_widget_1.setWidget(self.second_statusbar)
        MainWindow.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock_widget_1)

        # Создаем второй QDockWidget для второго статус бара
        self.dock_widget_2 = QtWidgets.QDockWidget("", MainWindow)
        self.dock_widget_2.setObjectName("dock_widget_2")
        self.dock_widget_2.setWidget(self.statusbar)
        MainWindow.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dock_widget_2)

        # Устанавливаем новый шрифт для всего второго статус бара
        font = self.second_statusbar.font()
        font.setPointSize(10)  # Установите желаемый размер шрифта
        self.second_statusbar.setFont(font)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Печать значков"))
        self.pushButton.setText(_translate("MainWindow", "Обновить базу"))
        self.pushButton_2.setText(_translate("MainWindow", "Статистика"))
        self.pushButton_3.setText(_translate("MainWindow", "Загрузить файл"))
        self.pushButton_4.setText(_translate("MainWindow", "Печать стикеров"))
        self.pushButton_5.setText(_translate("MainWindow", "Печать обложек"))
        self.pushButton_6.setText(_translate("MainWindow", "Печать значков"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.current_dir = Path.cwd()
        self.move(550, 100)
        self.count_printer = 0
        self.column_counter_printer = 0

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setGeometry(10, 10, 100, 25)
        self.progress_bar.setMaximum(100)
        self.statusbar.addWidget(self.progress_bar, 1)
        try:
            printers_list = enum_printers()
            for printer in printers_list:
                self.addPrinterCheckbox(printer)
        except Exception as ex:
            logger.debug(ex)

        self.pushButton.clicked.connect(self.evt_btn_update)
        self.pushButton_3.clicked.connect(self.evt_btn_open_file_clicked)

    def addPrinterCheckbox(self, printer_name):
        checkbox = QCheckBox(printer_name, self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(14)
        checkbox.setFont(font)
        checkbox.setObjectName(printer_name)
        self.gridLayout.addWidget(checkbox, self.column_counter_printer, self.count_printer)
        self.count_printer += 1
        if self.count_printer == 2:
            self.column_counter_printer += 1
            self.count_printer = 0

    def update_progress(self, current_value, total_value):
        progress = int(current_value / total_value * 100)
        self.progress_bar.setValue(progress)
        QApplication.processEvents()

    def restart(self):
        os.execl(sys.executable, os.path.abspath(__file__), *sys.argv)

    def evt_btn_open_file_clicked(self):
        """Ивент на кнопку загрузить файл"""
        res, _ = QFileDialog.getOpenFileName(self, 'Загрузить файл', str(self.current_dir), 'Лист XLSX (*.xlsx)')
        if res:
            self.lineEdit.setText(res)

    def evt_btn_update(self):
        """Ивент на кнопку обновить базу"""
        try:
            list_arts = update_db(self)
            mes = "\n".join(list_arts)
            dialog = CustomDialog()
            dialog.set_text(mes)
            dialog.exec_()
            download_new_arts_in_comp(list_arts, self)
            main_download_stickers(self)
        except Exception as ex:
            logger.error(ex)


if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
