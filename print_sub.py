import itertools
import os
import subprocess
import sys
import time

from PyQt5.QtWidgets import QMessageBox
from loguru import logger

from config import acrobat_path, ready_path
from db import Orders


def print_pdf_sticker(printer_name, self=None):
    # Проверка, поддерживается ли печать через subprocess на вашей платформе
    if sys.platform != 'win32':
        print("Печать PDF поддерживается только в Windows.")
    # Проверка наличия файла Adobe Acrobat Reader
    if not os.path.isfile(acrobat_path):
        print("Adobe Acrobat Reader не найден.")
        return
    bad_list_arts = []
    arts = Orders.select().order_by('num_on_List')
    try:
        print_processes = []
        # Открытие PDF-файла с использованием PyPDF2
        # with open(file_path, "rb") as f:
        for i in arts:
            # Формирование команды для печати файла
            if i.sticker:
                print_command = f'"{acrobat_path}" /N /T "{i.sticker}" "{printer_name}"'
                print_process = subprocess.Popen(print_command, shell=True)
                print_processes.append(print_process)
                time.sleep(0.5)
                logger.success(f'Файл {i.sticker} отправлен на печать на принтер {printer_name}')
            else:
                logger.error(f'Нет стикера на арт: {i.art}')
                bad_list_arts.append(i.art)
        if self and len(bad_list_arts) != 0:
            text_arts = "\n".join(bad_list_arts)
            QMessageBox.information(self, 'Отправка на печать', f'Нет стикеров на печать:\n{text_arts}')
    except Exception as e:
        logger.error(f'Возникла ошибка при печати файла: {e}')


def print_pdf_skin(printers):
    file_list = []
    tuple_printing = tuple()

    for file in os.listdir(f'{ready_path}'):
        if os.path.isfile(os.path.join(ready_path, file)):
            if file.split('.')[1] == 'pdf':
                file_path = os.path.join(ready_path, file)
                file_list.append(file_path)

    for file, printer in zip(file_list, itertools.cycle(printers)):
        tuple_printing += ((file, printer),)

    for file_path, printer_name in tuple_printing:
        try:
            print_processes = []
            print_command = f'"{acrobat_path}" /N /T "{file_path}" "{printer_name}"'
            print_process = subprocess.Popen(print_command, shell=True)
            print_processes.append(print_process)
            logger.success(f'Файл {file_path} отправлен на печать на принтер {printer_name}')
        except Exception as e:
            logger.error(f'Возникла ошибка при печати файла: {e}')


def print_png_images(printers):
    file_list = []
    tuple_printing = tuple()
    for root, dirs, files in os.walk(ready_path):
        for file in files:
            if file.endswith('png'):
                file_list.append(os.path.join(root, file))

    for file, printer in zip(file_list, itertools.cycle(printers)):
        tuple_printing += ((file, printer),)

    for file_path, printer_name in tuple_printing:
        # Проверка наличия файла
        try:
            subprocess.run(['mspaint', '/pt', file_path, printer_name], check=True)
            logger.success(f'Файл {file_path} отправлен на печать на принтер {printer_name}')
        except subprocess.CalledProcessError:
            print("Ошибка при печати файла.")


if __name__ == '__main__':
    file_path = r"E:\Новая база значков\AniKoya\Готовые\6\37\REZERO-4NEW-NABOR37\!10003.png"
    printer_name = "Отправить в OneNote 16"
    print_pdf_skin(printer_name)
