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


class ProgressBar:
    """Основной прогресс бар в проге"""

    def __init__(self, total, progress_bar, current=0):
        self.current = current
        self.total = total
        self.progress_bar = progress_bar

    def update_progress(self):
        self.current += 1
        self.progress_bar.update_progress(self.current, self.total)

    def __str__(self):
        return str(self.current)


def copy_image(image_path, count):
    folder_art = os.path.dirname(image_path)
    exp = image_path.split(".")[-1]
    for i in range(count - 1):
        shutil.copy2(image_path, os.path.join(folder_art, f"{i + 2}.{exp}"))


def remove_russian_letters(input_string):
    """Удаление русских букв из строки"""
    # Используем регулярное выражение для поиска всех русских букв
    russian_letters_pattern = re.compile("[а-яА-Я]")

    # Заменяем найденные русские буквы на пустую строку
    result_string = re.sub(russian_letters_pattern, "", input_string)

    return result_string.strip()


def delete_files_with_name(
    starting_directory: str, target_filename: str = "Картинка1.png"
):
    """Рекурсивное удаление файлов в директории с указанным названием target_filename"""
    count = 0
    for root, _, files in os.walk(starting_directory):
        for file in files:
            if file == target_filename:
                file_path = os.path.join(root, file)
                os.remove(file_path)
                count += 1
                # print(f"{count} Файл {file_path} удален.")


def df_in_xlsx(
    df: pd.DataFrame,
    filename: str,
    directory: str = "Файлы связанные с заказом",
    max_width: int = 50,
):
    """Запись датафрейма в эксель файл в указанную директорию"""
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


def rename_files(file_path: str, new_name: str):
    """Переименовывание файлов"""
    try:
        base_path = os.path.dirname(file_path)
        file_extension = os.path.splitext(file_path)[1]
        new_path = os.path.join(base_path, new_name + file_extension)
        os.rename(file_path, new_path)
        # logger.debug(f'Переименован файл {file_path} в {new_path}')
        return new_path
    except Exception as ex:
        logger.error(f"не удалось переименовать файл {file_path}\n{ex}")


def enum_printers(start=None) -> list:
    """Получение имен доступных принтеров, подключенных по USB портам"""
    flags = win32print.PRINTER_ENUM_LOCAL
    level = 2

    printers = win32print.EnumPrinters(flags, None, level)

    usb_printers = []

    for printer in printers:
        for port in printer["pPortName"].split(","):
            if port.strip().startswith("USB"):
                usb_printers.append(printer["pPrinterName"])

    # logger.info("Доступные принтеры, подключенные по USB: {}".format(", ".join(usb_printers)))
    return []


@dataclass
class FilesOnPrint:
    """
    Датаклас для работы с артикулами из заказа
    """

    art: str  # Артикул
    count: int  # Кол-во
    origin_art: Optional[str] = None  # Изначальный артикул до замены
    name: Optional[str] = None  # Тип
    status: str = "❌"  # Найден или нет в базе имеющихся артикулов ('✅')


def replace_bad_simbols(row: str) -> str:
    """Удаляет символы из строки которые нельзя указывать в названии файлов"""
    bad = r"[\?\/\\\:\*\"><\|]"
    new_row = re.sub(bad, "", row)
    return new_row


def split_row(row: str) -> list:
    """Разделяет строку по делителям"""
    delimiters = r"[\\/|, ]"
    substrings = re.split(delimiters, row)
    substrings = [i for i in substrings if i]
    return substrings


if __name__ == "__main__":
    import pandas as pd

    # Чтение данных из файла Excel
    df = pd.read_excel("2.xlsx")

    # Проверяем наличие столбца "Информация о заказе" и пропускаем первую строку, если он есть
    if "Информация о заказе" in df.columns:
        df = pd.read_excel("2.xlsx", skiprows=1)

    # Переименовываем столбцы
    df = df.rename(columns={"Ваш SKU": "Артикул продавца"})

    # Оставляем только нужные столбцы
    df = df.loc[:, ["Артикул продавца", "Количество"]]

    # Фильтруем строки по содержанию подстрок
    keywords = ["25", "37", "44", "56", "Popsocket", "popsocket", "POPSOCKET"]
    df = df[df["Артикул продавца"].str.contains("|".join(keywords))]
