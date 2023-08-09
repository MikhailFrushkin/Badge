import os
import shutil
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import win32print
from loguru import logger
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

from config import anikoya_path
from db import Article


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


def delete_files_with_name(starting_directory, target_filename="Картинка1.png"):
    count = 0
    for root, _, files in os.walk(starting_directory):
        for file in files:
            if file == target_filename:
                file_path = os.path.join(root, file)
                os.remove(file_path)
                count += 1
                print(f"{count} Файл {file_path} удален.")


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
    workbook.save(f"{filename}.xlsx")


def move_ready_folder(directory=rf'{anikoya_path}\Скаченные с диска',
                      target_directory=rf'{anikoya_path}\Готовые\Новые',
                      shop='AniKoya'):
    for folder in os.listdir(directory):

        try:
            folder_path = os.path.abspath(os.path.join(directory, folder))
            target_directory = os.path.abspath(target_directory)
            for i in os.listdir(folder_path):
                if os.path.isdir(os.path.join(folder_path, i)):
                    new_folder = os.path.join(folder_path, i)
                    if not os.path.exists(os.path.join(target_directory, i)):
                        shutil.move(new_folder, target_directory)
                        Article.create_with_art(i, os.path.join(target_directory, i), shop=shop)
                        # logger.debug(f'Перенос из {folder_path} -> {os.path.join(target_directory, folder)}')
            shutil.rmtree(directory)
        except Exception as ex:
            logger.error(ex)


def rename_files(file_path, new_name):
    try:
        base_path = os.path.dirname(file_path)
        file_extension = os.path.splitext(file_path)[1]
        new_path = os.path.join(base_path, new_name + file_extension)
        os.rename(file_path, new_path)
        # logger.debug(f'Переименован файл {file_path} в {new_path}')
        return new_path
    except Exception as ex:
        logger.error(f'не удалось переименовать файл {file_path}\n{ex}')


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


@dataclass
class FilesOnPrint:
    art: str
    count: int
    name: Optional[str] = None
    status: str = '❌'
    # '✅'


def read_excel_file(file: str) -> list:
    df = pd.read_excel(file)
    if 'Название товара' not in df.columns:
        # Если столбца нет, то создаем его и заполняем значениями "Нет названия"
        df['Название товара'] = 'Нет названия'
    df = df.groupby('Артикул продавца').agg({
        'Название товара': 'first',
        'Стикер': 'count',
    }).reset_index()
    df_in_xlsx(df, 'Сгруппированный заказ')
    df = df.rename(columns={'Стикер': 'Количество'})

    files_on_print = []
    for index, row in df.iterrows():
        file_on_print = FilesOnPrint(art=row['Артикул продавца'].strip(), name=row['Название товара'],
                                     count=row['Количество'])
        files_on_print.append(file_on_print)

    return files_on_print


if __name__ == '__main__':
    move_ready_folder()
