import asyncio
import os
import shutil
import time
from datetime import timedelta
from pathlib import Path
from threading import Thread

import fitz
import pandas as pd
import qdarkstyle
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QFont
from PyQt5.QtWidgets import QApplication, QVBoxLayout, QTextEdit, QPushButton, QDialog, QMessageBox, QWidget, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QLabel, QCalendarWidget
from PyQt5.QtWidgets import (
    QFileDialog, QCheckBox, QProgressBar
)
from loguru import logger
from peewee import fn

from api_rest import main_download_site
from base.db import Article, Statistic, GoogleTable, db, Orders
from config import machine_name, sticker_path_all, BASE_DIR
from gui.main_window import Ui_MainWindow
from utils.created_images import created_good_images
from utils.delete_bad_arts import delete_arts
from utils.main import update_arts_db, update_sticker_path
from utils.print_sub import print_pdf_skin, print_png_images
from utils.read_excel import read_excel_file
from utils.upload_files import upload_statistic_files_async
from utils.utils import enum_printers, FilesOnPrint, df_in_xlsx, remove_russian_letters


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
            art_item = QTableWidgetItem(group.origin_art)
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



# class Dialog(QDialog):
#     def __init__(self, button_names):
#         super().__init__()
#         self.button_names = button_names
#         self.initUI()
#         self.dialogs = []
#
#     def initUI(self):
#         self.setWindowTitle("Выберите принтер для печати стикеров")
#
#         # Создаем контейнер и устанавливаем для него компоновку
#         container = QWidget(self)
#         layout = QVBoxLayout(container)
#
#         for button_name in self.button_names:
#             button = QPushButton(button_name, self)
#             button.clicked.connect(self.buttonClicked)
#             button.setStyleSheet("QPushButton { font-size: 18px; height: 50px; }")
#             layout.addWidget(button)
#
#         # Добавляем прогресс бар и надпись в контейнер
#         self.progress_label = QLabel(self)
#         self.progress_bar = QProgressBar(self)
#         layout.addWidget(self.progress_label)
#         layout.addWidget(self.progress_bar)
#
#         # Устанавливаем контейнер как главный виджет диалогового окна
#         self.setLayout(layout)
#         self.setFixedWidth(400)
#
#     def buttonClicked(self):
#         sender = self.sender()
#         logger.debug(f"Нажата кнопка: {sender.text()}")
#         try:
#             self.show()
#             print_pdf_sticker(printer_name=sender.text(), self=self)
#             self.reject()
#
#         except Exception as ex:
#             logger.error(ex)


class QueueDialog(QWidget):
    """
    Окно со спискос на печать
    """

    def __init__(self, files_on_print, title, name_doc, A3_flag=False, parent=None):
        super().__init__(parent)
        self.files_on_print = files_on_print
        self.setWindowTitle(title)
        self.A3_flag = A3_flag
        self.name_doc = os.path.abspath(name_doc).split('\\')[-1].replace('.xlsx', '')
        self.list_on_print = 0

        layout = QVBoxLayout(self)

        # Add checkbox with default value checked
        self.create_pdf_checkbox = QCheckBox("Создать 1 PDF файл", self)
        self.create_pdf_checkbox.setChecked(True)
        self.create_pdf_checkbox.setFont(QFont("Arial", 16))  # Set font size
        self.create_pdf_checkbox.setStyleSheet("QCheckBox { font-size: 16pt; }")  # Set font size using style sheet
        layout.addWidget(self.create_pdf_checkbox)

        self.tableWidget = QTableWidget(self)
        self.tableWidget.setColumnCount(4)  # Добавление колонки 3 колонок
        self.tableWidget.setMinimumSize(800, 300)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Артикул", "Замена", "Количество", "Найден"])  # заголовки

        font = self.tableWidget.font()
        font.setPointSize(14)
        self.tableWidget.setFont(font)

        self.tableWidget.setRowCount(len(self.files_on_print))

        for row, file_on_print in enumerate(self.files_on_print):
            origin_art_item = QTableWidgetItem(file_on_print.origin_art)
            art_item = QTableWidgetItem(file_on_print.art)
            count_item = QTableWidgetItem(str(file_on_print.count))
            status_item = QTableWidgetItem(str(file_on_print.status))
            self.tableWidget.setItem(row, 0, origin_art_item)
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

        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.progress_label = QLabel("Прогресс:", self)
        self.progress_label.setFont(font)
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

    def evt_btn_print_clicked(self):
        """Создание файлов для одной или несколько строк"""
        selected_data = self.get_selected_data()
        if selected_data:
            created_good_images(selected_data, self, self.A3_flag)
            try:
                path = os.path.join(BASE_DIR, 'Файлы на печать')
                os.startfile(path)
            except Exception as ex:
                logger.error(ex)
        else:
            QMessageBox.information(self, 'Отправка на печать', 'Ни одна строка не выбрана')

    def evt_btn_print_all_clicked(self):
        """Создание файлов всех строк с артикулами"""
        logger.debug(self.name_doc)
        all_data = self.get_all_data()
        if all_data:
            try:
                asyncio.run(upload_statistic_files_async(os.path.basename(self.name_doc)))
            except Exception as ex:
                logger.error(ex)
            try:
                created_good_images(all_data, self, self.A3_flag)
                try:
                    path = os.path.join(BASE_DIR, 'Файлы на печать')
                    os.startfile(path)
                except Exception as ex:
                    logger.error(ex)
            except Exception as ex:
                logger.error(ex)
        else:
            QMessageBox.information(self, 'Отправка на печать', 'Таблица пуста')

    def get_selected_data(self):
        selected_rows = self.tableWidget.selectionModel().selectedRows()
        data = []
        for row in selected_rows:
            name = ''
            origin_art = self.tableWidget.item(row.row(), 0).text()
            art = self.tableWidget.item(row.row(), 1).text()
            count = self.tableWidget.item(row.row(), 2).text()
            status = self.tableWidget.item(row.row(), 3).text()
            if status == '✅':
                data.append(FilesOnPrint(name=name, origin_art=origin_art, art=art, count=int(count), status='✅'))
        return data

    def get_all_data(self):
        data = []
        for row in range(self.tableWidget.rowCount()):
            try:
                name = ''
                origin_art = self.tableWidget.item(row, 0).text()
                art = self.tableWidget.item(row, 1).text()
                count = self.tableWidget.item(row, 2).text().replace(".0", "")
                status = self.tableWidget.item(row, 3).text()
                if status == '✅':
                    data.append(FilesOnPrint(name=name, art=art, origin_art=origin_art, count=int(count), status='✅'))
            except Exception as ex:
                logger.error(ex)
        return data

    def update_progress(self, current_value, total_value):
        progress = int(current_value / total_value * 100)
        self.progress_bar.setValue(progress)
        QApplication.processEvents()


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.version = 13.0
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

        self.pushButton.clicked.connect(self.evt_btn_update)
        self.pushButton_3.clicked.connect(self.evt_btn_open_file_clicked)
        self.pushButton_8.clicked.connect(lambda: self.evt_btn_create_files(False))
        self.pushButton_9.clicked.connect(lambda: self.evt_btn_create_files(True))
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

        def get_download_path():
            return os.path.join(os.path.expanduser('~'), 'downloads')

        try:
            file_name, _ = QFileDialog.getOpenFileName(self, 'Загрузить файл', get_download_path(),
                                                       'CSV файлы (*.csv *.xlsx)')
        except Exception as ex:
            logger.error(ex)
            file_name, _ = QFileDialog.getOpenFileName(self, 'Загрузить файл', str(self.current_dir),
                                                       'CSV файлы (*.csv *.xlsx)')
        if file_name:
            try:
                self.lineEdit.setText(file_name)
                counts_art = read_excel_file(self.lineEdit.text())
                values = [f"{item.origin_art}: {item.count} шт." for item in counts_art]
                self.update_list_view(values)
            except Exception as ex:
                logger.error(f'ошибка чтения xlsx {ex}')
                QMessageBox.information(self, 'Инфо', f'ошибка чтения xlsx {ex}')

    def evt_btn_create_files(self, flag_A3):
        """Ивент на кнопку Создать файлы"""
        filename = self.lineEdit.text()

        if filename:
            try:
                counts_art = read_excel_file(filename)
                for item in counts_art:
                    status = None
                    try:
                        art = remove_russian_letters(item.art.upper())
                        status = Article.get_or_none(fn.UPPER(Article.art) == art)
                    except Exception as ex:
                        logger.error(ex)
                    if status and os.path.exists(status.folder):
                        item.status = '✅'
                counts_art = sorted(counts_art, key=lambda x: x.status, reverse=True)
                # try:
                #     bad_arts = [(i.art, i.count) for i in counts_art
                #                 if i.status == '❌']
                #     if bad_arts:
                #         df_bad = pd.DataFrame(bad_arts, columns=['Артикул', 'Количество'])
                #         df_in_xlsx(df_bad, f'Не найденные артикула в заказе '
                #                            f'{os.path.basename(filename)}_v_{self.version}_{machine_name}')
                #
                # except Exception as ex:
                #     logger.error(ex)
            except Exception as ex:
                logger.error(ex)

            try:
                if counts_art:
                    dialog = QueueDialog(counts_art, 'Значки', filename, flag_A3)
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
            logger.warning('Обновление базы с сайта')
            try:
                main_download_site()
            except Exception as ex:
                logger.error(ex)
            try:
                logger.warning('Проверка базы')
                update_arts_db()
                update_sticker_path()
            except Exception as ex:
                logger.error(ex)
            directory_path_sticker = sticker_path_all
            # try:
            #     logger.debug('Загрузка стикеров я.диска:')
            #     main_search_sticker(directory_path_sticker, token, folder_path='/Новая база (1)')
            # except Exception as ex:
            #     logger.error(ex)
            # try:
            #     logger.debug('Загрузка стикеров я.диска 2:')
            #     main_search_sticker(directory_path_sticker, token2, folder_path='/Новая база')
            # except Exception as ex:
            #     logger.error(ex)
            # try:
            #     update_base_postgresql()
            # except Exception as ex:
            #     logger.error(ex)

            QMessageBox.information(self, 'Загрузка', 'Загрузка закончена')
            self.progress_bar.setValue(100)
        except Exception as ex:
            logger.error(ex)

    def evt_btn_print_stickers(self):
        """Ивент на кнопку напечатать стикеры"""
        if self.lineEdit.text() != '':
            def find_files_in_directory(directory, arts_list):
                found_files = []
                not_found_files = []
                sticker_dict = {}
                for file in os.listdir(directory):
                    file_name_no_exp = file.replace(".pdf", "")
                    file_name = file_name_no_exp.lower().replace(' ', '').strip()
                    sticker_dict[file_name] = os.path.join(directory, file)
                for art in arts_list:
                    file_name = art.origin_art.lower().strip().replace(' ', '')
                    if file_name in sticker_dict:
                        found_files.append(sticker_dict[file_name])
                    else:
                        not_found_files.append(art.origin_art)
                logger.debug(not_found_files)
                return found_files, not_found_files

            def merge_pdfs_stickers(arts_paths, output_path):
                pdf_writer = fitz.open()  # Создаем новый PDF

                for input_path in arts_paths:
                    try:
                        pdf_reader = fitz.open(input_path)  # Открываем PDF
                        pdf_writer.insert_pdf(pdf_reader)  # Вставляем страницы
                        pdf_reader.close()  # Закрываем PDF
                    except Exception as e:
                        print(f"Error processing {input_path}: {e}")

                pdf_writer.save(f"{output_path}.pdf")  # Сохраняем итоговый PDF
                pdf_writer.close()  # Закрываем итоговый PDF

            def create_order_shk(arts, name_doc=""):
                found_files_stickers, not_found_stickers = find_files_in_directory(sticker_path_all,
                                                                                   arts)
                if found_files_stickers:
                    logger.debug(found_files_stickers)
                    merge_pdfs_stickers(found_files_stickers, f'Файлы на печать\\!ШК {name_doc}')
                    logger.success(f'{name_doc} ШК сохранены!')
                else:
                    logger.error(f'{name_doc} ШК не найдены!')
                return not_found_stickers

            arts = read_excel_file(self.lineEdit.text())
            not_found_stickers_arts = create_order_shk(arts, "Все ")
            if not_found_stickers_arts:
                QMessageBox.warning(self, 'Проблема', f'Не найдены шк для:\n{", ".join(not_found_stickers_arts)}')
            try:
                os.startfile(BASE_DIR)
            except Exception as ex:
                logger.error(ex)
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
                logger.debug(widget.text())
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
                logger.error(ex)


def run_script():
    while True:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.warning('Поиск артикулов для замены')
        try:
            delete_arts()
        except Exception as ex:
            logger.error(ex)

        logger.warning('Обновление базы с сайта')
        try:
            main_download_site()
        except Exception as ex:
            logger.error(ex)

        # logger.success('Обновление готовых файлов')
        # try:
        #     missing_dict = missing_folders()
        #     loop.run_until_complete(main_parser(missing_dict))
        # except Exception as ex:
        #     logger.error(ex)

        logger.debug('Проверка базы...')
        update_arts_db()
        # try:
        #     update_base_postgresql()
        # except Exception as ex:
        #     logger.error(ex)
        directory_path_sticker = sticker_path_all
        # try:
        #     logger.debug('Загрузка стикеров я.диска:')
        #     main_search_sticker(directory_path_sticker, token, folder_path='/Новая база (1)')
        # except Exception as ex:
        #     logger.error(ex)
        # try:
        #     logger.debug('Загрузка стикеров я.диска 2:')
        #     main_search_sticker(directory_path_sticker, token2, folder_path='/Новая база')
        # except Exception as ex:
        #     logger.error(ex)

        try:
            update_sticker_path()
        except Exception as ex:
            logger.error(ex)

        logger.success('Обновление завершено')
        time.sleep(5 * 60)


if __name__ == '__main__':
    import sys

    shutil.rmtree('temp', ignore_errors=True)
    db.connect()
    db.create_tables([Statistic, GoogleTable, Orders, Article], safe=True)
    db.close()
    directories = ['logs', 'base', 'Файлы на печать']
    for dir_name in directories:
        os.makedirs(dir_name, exist_ok=True)
    logger.add(
        "logs/logs.log",
        rotation="20 MB",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file!s} | {line} | {message}"
    )

    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    w = MainWindow()
    w.show()
    if machine_name != 'ADMIN':
        script_thread = Thread(target=run_script)
        script_thread.daemon = True
        script_thread.start()

    sys.exit(app.exec())
