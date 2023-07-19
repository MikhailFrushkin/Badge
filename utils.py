import os
import shutil

from loguru import logger
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

from config import anikoya_path, Article
import win32api
import win32con
import win32print


class ProgressBar:
    def __init__(self, total, progress_bar, current=0):
        self.current = current
        self.total = total
        self.progress_bar = progress_bar

    def update_progress(self):
        self.current += 1
        self.progress_bar.update_progress(self.current, self.total)

    def __str__(self):
        return str(self.current)


def df_in_xlsx(df, filename, max_width=50):
    # Создание нового рабочего книги Excel
    workbook = Workbook()
    # Создание нового листа в рабочей книге
    sheet = workbook.active
    # Конвертация DataFrame в строки данных
    for row in dataframe_to_rows(df, index=False, header=True):
        sheet.append(row)
        # Ограничение ширины колонок
    for column in sheet.columns:
        column_letter = column[0].column_letter
        max_length = max(len(str(cell.value)) for cell in column)
        adjusted_width = min(max_length + 2, max_width)
        sheet.column_dimensions[column_letter].width = adjusted_width
    # Сохранение рабочей книги в файл
    workbook.save(f"files/{filename}.xlsx")


def move_ready_folder(directory=rf'{anikoya_path}\Скаченные с диска',
                      target_directory=rf'{anikoya_path}\Новые',
                      shop='AniKoya'):
    for folder in os.listdir(directory):
        try:
            folder_path = os.path.join(directory, folder)

            for i in os.listdir(folder_path):
                if os.path.isdir(os.path.join(folder_path, i)):
                    if not os.path.exists(os.path.join(target_directory, i)):
                        shutil.move(os.path.join(folder_path, i), target_directory)
                        Article.create_with_art(i, os.path.join(target_directory, i), shop=shop)
                        logger.debug(f'Перенос из {folder_path} -> {os.path.join(target_directory, folder)}')

            shutil.rmtree(directory)
        except Exception as ex:
            logger.error(ex)


def rename_files(file_path, new_name):
    try:
        base_path = os.path.dirname(file_path)
        file_extension = os.path.splitext(file_path)[1]
        new_path = os.path.join(base_path, new_name + file_extension)
        os.rename(file_path, new_path)
        logger.debug(f'Переименован файл {file_path} в {new_path}')
    except Exception as ex:
        logger.error(f'не удалось переименовать файл {file_path}\n{ex}')
    return new_path


def enum_printers(start=None) -> list:
    """Получение имен доступных принтеров, подключенных по USB портам"""
    flags = win32print.PRINTER_ENUM_LOCAL
    level = 2

    printers = win32print.EnumPrinters(flags, None, level)

    usb_printers = []

    for printer in printers:
        for port in printer['pPortName'].split(','):
            if not port.strip().startswith('USB'):
                usb_printers.append(printer['pPrinterName'])

    logger.info("Доступные принтеры, подключенные по USB: {}".format(", ".join(usb_printers)))
    return usb_printers
