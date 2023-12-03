import os
import re
import shutil
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import win32print
from loguru import logger
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from peewee import fn

from blur import blur_image
from config import anikoya_path, all_badge
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
                # print(f"{count} Файл {file_path} удален.")


def df_in_xlsx(df, filename, directory='Файлы связанные с заказом', max_width=50):
    workbook = Workbook()
    sheet = workbook.active
    for row in dataframe_to_rows(df, index=False, header=True):
        sheet.append(row)
    for column in sheet.columns:
        column_letter = column[0].column_letter
        max_length = max(len(str(cell.value)) for cell in column)
        adjusted_width = min(max_length + 2, max_width)
        sheet.column_dimensions[column_letter].width = adjusted_width

    os.makedirs(directory, exist_ok=True)
    workbook.save(f"{directory}\\{filename}.xlsx")


def move_ready_folder(directory=f'{all_badge}\\Скаченные с диска',
                      target_directory=f'{anikoya_path}',
                      shop='AniKoya'):
    for folder in os.listdir(directory):
        try:
            folder_path = os.path.abspath(os.path.join(directory, folder))
            target_directory = os.path.abspath(target_directory)

            for i in os.listdir(folder_path):
                new_folder = os.path.join(folder_path, i)
                if os.path.isdir(new_folder):
                    if not os.path.exists(os.path.join(target_directory, i)):
                        shutil.move(new_folder, target_directory)
                        Article.create_with_art(i, os.path.join(target_directory, i), shop=shop)
                        try:
                            art = Article.get_or_none(fn.UPPER(Article.art) == i.upper())
                            if art:
                                folder_name = art.folder
                                for index, filename in enumerate(os.listdir(folder_name), start=1):
                                    if (filename.startswith('!') or filename[0].isdigit()) \
                                            and os.path.isfile(os.path.join(folder_name, filename)):
                                        try:
                                            blur_image(image_path=os.path.join(folder_name, filename),
                                                       output_path=os.path.join(folder_name, filename),
                                                       size_b=art.size)
                                        except Exception as ex:
                                            logger.error(ex)
                                            logger.error(os.path.join(folder_name, filename))
                            else:
                                logger.error(f'Не нашелся артикул в бд {i}')
                        except Exception as ex:
                            logger.error(ex)
                    else:
                        logger.error(f'{os.path.join(target_directory, i)} существует')
        except Exception as ex:
            logger.error(ex)
        finally:
            shutil.rmtree(directory)
    return True


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
            if port.strip().startswith('USB'):
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
    """Чтенеие файла с заказом"""
    df = pd.DataFrame()
    try:
        shutil.rmtree('Файлы связанные с заказом', ignore_errors=True)
    except:
        pass
    if file.endswith('.csv'):
        try:
            df = pd.read_csv(file, delimiter=';')
            if 'Название товара' not in df.columns:
                df['Название товара'] = 'Нет названия'
            df = df.groupby('Артикул').agg({
                'Название товара': 'first',
                'Номер заказа': 'count',
            }).reset_index()

            mask = ~df['Артикул'].str.startswith('POSTER')
            df = df[mask]

            df = df.rename(columns={'Номер заказа': 'Количество', 'Артикул': 'Артикул продавца'})
        except Exception as ex:
            logger.error(ex)
    else:
        try:
            df = pd.read_excel(file)
            columns_list = list(map(str.lower, df.columns))
            if len(columns_list) == 2:
                logger.debug(f'Столбцы: {df.columns}')
                try:
                    df = df.rename(columns={df.columns[0]: 'Артикул продавца', df.columns[1]: 'Количество'})
                except Exception as ex:
                    logger.error(ex)
                    df = df.rename(columns={'Aртикул': 'Артикул продавца'})
            else:
                df = df.groupby('Артикул продавца').agg({
                    'Стикер': 'count',
                }).reset_index()
                df = df.rename(columns={'Стикер': 'Количество'})
        except Exception as ex:
            logger.error(ex)

    df_in_xlsx(df, 'Сгруппированный заказ')

    files_on_print = []
    try:
        for index, row in df.iterrows():
            if '-poster-' in row['Артикул продавца'].lower():
                file_on_print = FilesOnPrint(art=replace_bad_simbols(row['Артикул продавца'].strip().lower()),
                                             count=row['Количество'])
                files_on_print.append(file_on_print)
            elif 'poster-' not in row['Артикул продавца'].lower():
                file_on_print = FilesOnPrint(art=replace_bad_simbols(row['Артикул продавца'].strip().lower()),
                                             count=row['Количество'])
                files_on_print.append(file_on_print)
    except Exception as ex:
        logger.error(ex)
    return files_on_print


def replace_bad_simbols(row):
    bad = r'[\?\/\\\:\*\"><\|]'
    new_row = re.sub(bad, '', row)
    return new_row




if __name__ == '__main__':
    # read_excel_file(r'E:\PyCharm\Badge2\0611 5 Ангелина 44.xlsx')
    # read_excel_file(r'E:\PyCharm\Badge2\Заказ.xlsx')
    pass
