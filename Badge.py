import asyncio
import os
from datetime import timedelta
from pathlib import Path

import pandas as pd
import qdarkstyle
import requests
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QTextEdit, QPushButton, QDialog, QMessageBox, QWidget, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QLabel, QCalendarWidget
from PyQt5.QtWidgets import (
    QFileDialog, QCheckBox, QProgressBar
)
from loguru import logger
from peewee import fn

from config import all_badge, token
from created_images import created_good_images
from db import Article, Statistic, update_base_postgresql, GoogleTable, Orders, db
from dow_stickers import main_download_stickers
from main import update_db, download_new_arts_in_comp, update_arts_db2, update_sticker_path
from print_sub import print_pdf_sticker, print_pdf_skin, print_png_images
from upload_files import upload_statistic_files_async
from utils import enum_printers, read_excel_file, FilesOnPrint, delete_files_with_name, df_in_xlsx


def check_file(self):
    headers = {
        "Authorization": f"OAuth {token}"
    }

    params = {
        "path": 'Программы',
        "fields": "_embedded.items.name"  # Запрашиваем только имена файлов
    }

    response = requests.get("https://cloud-api.yandex.net/v1/disk/resources", headers=headers, params=params)

    if response.status_code == 200:
        files = response.json()["_embedded"]["items"]
        if 'Печать значков.txt' in [file["name"] for file in files]:
            return True
        else:
            return False
    else:
        print("Error:", response.status_code)
        return []


class GroupedRecordsDialog(QDialog):
    def __init__(self, parent, start_date, end_date):
        super(GroupedRecordsDialog, self).__init__(parent)
        self.setWindowTitle('Статистика печати')
        self.start_date = start_date
        self.end_date = end_date
        self.layout = QVBoxLayout(self)
        self.table_widget = QTableWidget(self)
        self.layout.addWidget(self.table_widget)
        self.populate_table()

        # Set the size of the dialog based on the table size
        self.adjust_dialog_size()

    def populate_table(self):
        self.table_widget.setColumnCount(3)  # Add one more column for "Sum of nums"
        self.table_widget.setHorizontalHeaderLabels(["Артикул", "Количество", "Количество значков"])
        end_date_inclusive = self.end_date.toPython() + timedelta(days=1)
        records = Statistic.select().where(
            (Statistic.created_at >= self.start_date.toPython()) &
            (Statistic.created_at < end_date_inclusive)
        )

        grouped_records = records.group_by(Statistic.art).select(
            Statistic.art,
            Statistic.size,
            fn.COUNT(Statistic.id).alias('count'),
            fn.SUM(Statistic.nums).alias('sum_of_nums')
        )
        data = []
        row = 0
        for group in grouped_records:
            art_item = QTableWidgetItem(group.art)
            count_item = QTableWidgetItem(str(group.count))
            sum_of_nums_item = QTableWidgetItem(str(group.sum_of_nums))
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, art_item)
            self.table_widget.setItem(row, 1, count_item)
            self.table_widget.setItem(row, 2, sum_of_nums_item)
            row += 1
            data.append({'Артикул': group.art, 'Размер': group.size, 'Количество': group.count,
                         'Сумма значков': group.sum_of_nums})
        df = pd.DataFrame(data)
        size_list = df['Размер'].unique().tolist()
        os.makedirs('Файлы статистики', exist_ok=True)
        if size_list:
            for size in size_list:
                df_temp = df[df['Размер'] == str(size)]
                df_in_xlsx(df_temp, f'Статистика {size}', directory='Файлы статистики')
        self.table_widget.resizeColumnsToContents()

    def adjust_dialog_size(self):
        table_width = self.table_widget.sizeHint().width()
        dialog_width = max(table_width + 280, 420)  # Minimum width of 400 pixels
        self.setFixedWidth(dialog_width)
        self.adjustSize()


class DateRangeDialog(QDialog):
    def __init__(self, parent=None):
        super(DateRangeDialog, self).__init__(parent)
        layout = QVBoxLayout(self)
        self.calendar = QCalendarWidget(self)
        layout.addWidget(self.calendar)
        self.ok_button = QPushButton('OK', self)
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.on_ok_button_clicked)
        layout.addWidget(self.ok_button)
        self.selected_dates = []
        self.calendar.clicked.connect(self.on_calendar_clicked)

    def on_calendar_clicked(self, date):
        if len(self.selected_dates) == 2:
            logger.debug(self.selected_dates)
            self.clear_selection()
        if len(self.selected_dates) < 2:
            self.selected_dates.append(date)
            self.selected_dates.sort()

        self.ok_button.setEnabled(len(self.selected_dates) == 2)
        self.update_date_highlight()

    def update_date_highlight(self):
        palette = self.calendar.palette()
        palette.setColor(QPalette.Highlight, Qt.transparent)
        self.calendar.setPalette(palette)

        if len(self.selected_dates) == 2:
            current_date = self.selected_dates[0]
            while current_date <= self.selected_dates[1]:
                self.calendar.setDateTextFormat(current_date, self.date_format_for_highlight())
                current_date = current_date.addDays(1)

    def date_format_for_highlight(self):
        date_format = self.calendar.dateTextFormat(self.selected_dates[0])
        date_format.setBackground(Qt.lightGray)
        return date_format

    def on_ok_button_clicked(self):
        self.accept()

    def reject(self):
        self.clear_selection()
        super(DateRangeDialog, self).reject()

    def clear_selection(self):
        try:
            self.selected_dates = []
            self.update_date_highlight()
        except Exception as ex:
            logger.error(ex)


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


class Dialog(QDialog):
    def __init__(self, button_names):
        super().__init__()
        self.button_names = button_names
        self.initUI()
        self.dialogs = []

    def initUI(self):
        self.setWindowTitle("Выберите принтер для печати стикеров")

        # Создаем контейнер и устанавливаем для него компоновку
        container = QWidget(self)
        layout = QVBoxLayout(container)

        for button_name in self.button_names:
            button = QPushButton(button_name, self)
            button.clicked.connect(self.buttonClicked)
            button.setStyleSheet("QPushButton { font-size: 18px; height: 50px; }")
            layout.addWidget(button)

        # Добавляем прогресс бар и надпись в контейнер
        self.progress_label = QLabel(self)
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        # Устанавливаем контейнер как главный виджет диалогового окна
        self.setLayout(layout)
        self.setFixedWidth(400)

    def buttonClicked(self):
        sender = self.sender()
        print(f"Нажата кнопка: {sender.text()}")
        try:
            self.show()
            print_pdf_sticker(printer_name=sender.text(), self=self)
            self.reject()

        except Exception as ex:
            logger.error(ex)


class QueueDialog(QWidget):
    def __init__(self, files_on_print, title, name_doc, sub_self, A3_flag=False, parent=None):
        super().__init__(parent)
        self.files_on_print = files_on_print
        self.setWindowTitle(title)
        self.sub_self = sub_self
        self.A3_flag = A3_flag
        self.name_doc = os.path.abspath(name_doc).split('\\')[-1].replace('.xlsx', '')
        self.list_on_print = 0

        layout = QVBoxLayout(self)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(4)  # Добавление колонки "Название"
        self.tableWidget.setMinimumSize(800, 300)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Название", "Артикул", "Количество", "Найден"])  # Обновленные заголовки

        font = self.tableWidget.font()
        font.setPointSize(14)
        self.tableWidget.setFont(font)

        self.tableWidget.setRowCount(len(self.files_on_print))

        for row, file_on_print in enumerate(self.files_on_print):
            name_item = QTableWidgetItem(file_on_print.name)  # Получение названия из датакласса
            art_item = QTableWidgetItem(file_on_print.art)
            count_item = QTableWidgetItem(str(file_on_print.count))
            status_item = QTableWidgetItem(str(file_on_print.status))
            self.tableWidget.setItem(row, 0, name_item)  # Установка элемента в колонку "Название"
            self.tableWidget.setItem(row, 1, art_item)
            self.tableWidget.setItem(row, 2, count_item)
            self.tableWidget.setItem(row, 3, status_item)

        layout.addWidget(self.tableWidget)

        font = self.tableWidget.font()

        print_button = QPushButton("Создать", self)
        print_button.setFont(font)
        print_button.clicked.connect(self.evt_btn_print_clicked)
        layout.addWidget(print_button)

        print_all_button = QPushButton("Создать все файлы со значками", self)
        print_all_button.setFont(font)
        print_all_button.clicked.connect(self.evt_btn_print_all_clicked)
        layout.addWidget(print_all_button)

        # Установка режима выделения целых строк
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Установка ширины колонки "Артикул" в 80% от ширины окна
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.progress_label = QLabel("Прогресс:", self)
        self.progress_label.setFont(font)
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

    def evt_btn_print_clicked(self):
        selected_data = self.get_selected_data()
        if selected_data:
            logger.debug(selected_data)
            created_good_images(selected_data, self, self.A3_flag)
        else:
            QMessageBox.information(self, 'Отправка на печать', 'Ни одна строка не выбрана')

    def evt_btn_print_all_clicked(self):
        all_data = self.get_all_data()
        if all_data:
            logger.debug(all_data)
            created_good_images(all_data, self, self.A3_flag)
        else:
            QMessageBox.information(self, 'Отправка на печать', 'Таблица пуста')

    def get_selected_data(self):
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        data = []
        for row in selected_rows:
            name = self.tableWidget.item(row.row(), 0).text()
            art = self.tableWidget.item(row.row(), 1).text()
            count = self.tableWidget.item(row.row(), 2).text()
            status = self.tableWidget.item(row.row(), 3).text()
            if status == '✅':
                data.append(FilesOnPrint(name=name, art=art, count=int(count), status='✅'))
        return data

    def get_all_data(self):
        data = []
        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.item(row, 0).text()
            art = self.tableWidget.item(row, 1).text()
            count = self.tableWidget.item(row, 2).text()
            status = self.tableWidget.item(row, 3).text()
            if status == '✅':
                data.append(FilesOnPrint(name=name, art=art, count=int(count), status='✅'))
        return data

    def update_progress(self, current_value, total_value):
        progress = int(current_value / total_value * 100)
        self.progress_bar.setValue(progress)
        QApplication.processEvents()


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

        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.pushButton_6 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_6.setFont(font)
        self.pushButton_6.setObjectName("pushButton_6")
        self.gridLayout_2.addWidget(self.pushButton_6, 2, 1, 1, 1)
        self.pushButton_5 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_5.setFont(font)
        self.pushButton_5.setObjectName("pushButton_5")
        self.gridLayout_2.addWidget(self.pushButton_5, 2, 2, 1, 1)
        self.pushButton_4 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_4.setFont(font)
        self.pushButton_4.setObjectName("pushButton_4")
        self.gridLayout_2.addWidget(self.pushButton_4, 2, 3, 1, 1)

        self.pushButton_8 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_8.setFont(font)
        self.pushButton_8.setObjectName("pushButton_8")
        self.gridLayout_2.addWidget(self.pushButton_8, 0, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_2)

        self.pushButton_9 = QtWidgets.QPushButton(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily("Times New Roman")
        font.setPointSize(15)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.pushButton_9.setFont(font)
        self.pushButton_9.setObjectName("pushButton_9")
        self.gridLayout_2.addWidget(self.pushButton_9, 1, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_2)

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
        self.pushButton_6.setText(_translate("MainWindow", "Печать стикеров"))
        self.pushButton_5.setText(_translate("MainWindow", "Печать обложек"))
        self.pushButton_4.setText(_translate("MainWindow", "Печать значков"))
        self.pushButton_8.setText(_translate("MainWindow", "Создать файлы"))
        self.pushButton_9.setText(_translate("MainWindow", "Создать файлы A3"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.current_dir = Path.cwd()
        self.dialogs = []

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

        try:
            if not check_file(self):
                self.pushButton.setEnabled(False)
                self.pushButton_3.setEnabled(False)
                self.pushButton_8.setEnabled(False)
                self.pushButton_9.setEnabled(False)
                self.pushButton_6.setEnabled(False)
                self.pushButton_5.setEnabled(False)
                self.pushButton_4.setEnabled(False)
                self.pushButton_2.setEnabled(False)
        except Exception as ex:
            logger.debug(ex)

        self.pushButton.clicked.connect(self.evt_btn_update)
        self.pushButton_3.clicked.connect(self.evt_btn_open_file_clicked)
        self.pushButton_8.clicked.connect(self.evt_btn_create_files)
        self.pushButton_9.clicked.connect(self.evt_btn_create_files_A3)
        self.pushButton_6.clicked.connect(self.evt_btn_print_stickers)
        self.pushButton_5.clicked.connect(self.evt_btn_print_skins)
        self.pushButton_4.clicked.connect(self.evt_btn_print_images)
        self.pushButton_2.clicked.connect(self.on_open_dialog_button_clicked)

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
        file_name, _ = QFileDialog.getOpenFileName(self, 'Загрузить файл', str(self.current_dir),
                                                   'CSV файлы (*.csv *.xlsx)')
        if file_name:
            try:
                self.lineEdit.setText(file_name)
                counts_art = read_excel_file(self.lineEdit.text())
                values = [f"{item.art}: {item.count} шт." for item in counts_art]
                self.update_list_view(values)
            except Exception as ex:
                logger.error(f'ошибка чтения xlsx {ex}')
                QMessageBox.information(self, 'Инфо', f'ошибка чтения xlsx {ex}')

    def evt_btn_create_files(self):
        """Ивент на кнопку Создать файлы"""
        filename = self.lineEdit.text()
        if filename:
            logger.success(filename)
            try:
                counts_art = read_excel_file(filename)
                for item in counts_art:
                    status = Article.get_or_none(Article.art == item.art)
                    if status and os.path.exists(status.folder):
                        item.status = '✅'
                counts_art = sorted(counts_art, key=lambda x: x.status, reverse=True)
                try:
                    bad_arts = [(i.art, i.count) for i in counts_art if i.status == '❌']
                    df_bad = pd.DataFrame(bad_arts, columns=['Артикул', 'Количество'])
                    df_in_xlsx(df_bad, f'Не найденные артикула в заказе {os.path.basename(filename)}')

                except Exception as ex:
                    logger.error(ex)
            except Exception as ex:
                logger.error(ex)
            try:
                if len(counts_art) > 0:
                    dialog = QueueDialog(counts_art, 'Значки', filename, self)
                    self.dialogs.append(dialog)
                    dialog.show()
                    try:
                        asyncio.run(upload_statistic_files_async(os.path.basename(filename)))
                    except Exception as ex:
                        logger.error(ex)
            except Exception as ex:
                logger.error(f'Ошибка формирования списков печати {ex}')

        else:
            QMessageBox.information(self, 'Инфо', 'Загрузите заказ')

    def evt_btn_create_files_A3(self):
        """Ивент на кнопку Создать файлы"""
        if self.lineEdit.text():
            try:
                counts_art = read_excel_file(self.lineEdit.text())
                for item in counts_art:
                    status = Article.get_or_none(Article.art == item.art)
                    if status:
                        item.status = '✅'
                counts_art = sorted(counts_art, key=lambda x: x.status, reverse=True)
            except Exception as ex:
                logger.error(ex)
            try:
                if len(counts_art) > 0:
                    dialog = QueueDialog(counts_art, 'Значки', self.lineEdit.text(), self, True)
                    self.dialogs.append(dialog)
                    dialog.show()
            except Exception as ex:
                logger.error(f'Ошибка формирования списков печати {ex}')
        else:
            QMessageBox.information(self, 'Инфо', 'Загрузите заказ')

    def update_list_view(self, values):
        model = QtCore.QStringListModel()
        model.setStringList(values)
        self.listView.setModel(model)

    def evt_btn_update(self):
        """Ивент на кнопку обновить базу"""
        try:
            list_arts = update_db(self)
            mes = "\n".join(list_arts)
            dialog = CustomDialog()
            dialog.set_text(mes)
            dialog.exec_()
            logger.debug('Загрузка стикеров:')
            main_download_stickers(self)

            download_new_arts_in_comp(list_arts, self)

            delete_files_with_name(starting_directory=all_badge)
            try:
                update_arts_db2()
                update_sticker_path()
            except Exception as ex:
                logger.error(ex)
            try:
                update_base_postgresql()
            except Exception as ex:
                logger.error(ex)
            QMessageBox.information(self, 'Загрузка', 'Загрузка закончена')
            self.progress_bar.setValue(100)
        except Exception as ex:
            logger.error(ex)

    def evt_btn_print_stickers(self):
        """Ивент на кнопку напечатать стикеры"""
        logger.info(self.lineEdit.text())
        if self.lineEdit.text() != '':
            button_names = enum_printers()
            dialog = Dialog(button_names=button_names)
            dialog.exec_()
        else:
            QMessageBox.information(self, 'Инфо', 'Загрузите заказ')

    def get_printers(self):
        # Список выбранных принтеров
        checked_checkboxes = []
        for i in range(self.gridLayout.count()):
            item = self.gridLayout.itemAt(i)
            # Получаем фактический виджет, если элемент является QLayoutItem
            widget = item.widget()
            # Проверяем, является ли виджет флажком (QCheckBox) и отмечен ли он
            if isinstance(widget, QtWidgets.QCheckBox) and widget.isChecked():
                checked_checkboxes.append(widget.text())
                print(widget.text())
        if not checked_checkboxes:
            QMessageBox.information(self, 'Инфо', 'Не выбран ни один принтер')
        return checked_checkboxes

    def evt_btn_print_skins(self):
        """Ивент на кнопку напечатать обложки"""
        try:
            print_pdf_skin(self.get_printers())
        except Exception as ex:
            logger.error(f'Ошибка печати обложек {ex}')

    def evt_btn_print_images(self):
        """Ивент на кнопку напечатать значки"""
        try:
            printers = self.get_printers()
            if printers:
                print_png_images(printers)
        except Exception as ex:
            logger.error(f'Ошибка печати обложек {ex}')

    def on_open_dialog_button_clicked(self):
        dialog = DateRangeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                start_date = dialog.selected_dates[0]
                end_date = dialog.selected_dates[1]
                if start_date and end_date:
                    date1 = start_date
                    date2 = end_date

                    end_date_inclusive = date2.toPython() + timedelta(days=1)
                    records = Statistic.select().where(
                        (Statistic.created_at >= date1.toPython()) &
                        (Statistic.created_at < end_date_inclusive)
                    )
                    count_of_records = records.count()

                    sum_of_nums = records.select(fn.SUM(Statistic.nums)).scalar()
                    logger.success(f'Количество артикулов: {count_of_records}\nКоличество значков: {sum_of_nums}')
                    QMessageBox.information(self, 'Общая статистика',
                                            f'Количество артикулов: {count_of_records}\n'
                                            f'Количество значков: {sum_of_nums}')

                    grouped_dialog = GroupedRecordsDialog(self, start_date, end_date)
                    grouped_dialog.exec_()


            except Exception as ex:
                print(ex)


if __name__ == '__main__':
    import sys

    db.connect()
    db.create_tables([Statistic, GoogleTable, Orders, Article])
    db.close()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
