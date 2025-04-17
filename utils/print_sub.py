import itertools
import os
import subprocess
import sys
import time

from PyQt5.QtWidgets import QMessageBox
from loguru import logger

from base.db import Orders
from config import acrobat_path, OUTPUT_READY_FILES


def print_pdf_sticker(printer_name, self=None):
    # Проверка, поддерживается ли печать через subprocess на вашей платформе
    if sys.platform != "win32":
        print("Печать PDF поддерживается только в Windows.")
    # Проверка наличия файла Adobe Acrobat Reader
    if not os.path.isfile(acrobat_path):
        print("Adobe Acrobat Reader не найден.")
        return
    bad_list_arts = []
    arts = Orders.select().order_by("num_on_list")
    sorted_arts = sorted([i for i in arts], key=lambda x: x.num_on_list)
    try:
        print_processes = []
        for i in sorted_arts:
            if i.sticker:
                print_command = f'"{acrobat_path}" /N /T "{i.sticker}" "{printer_name}"'
                print_process = subprocess.Popen(print_command, shell=True)
                print_processes.append(print_process)
                time.sleep(0.5)
                logger.success(
                    f"Файл {i.sticker} отправлен на печать на принтер {printer_name}"
                )
            else:
                logger.error(f"Нет стикера на арт: {i.art}")
                bad_list_arts.append(i.art)
        if self and len(bad_list_arts) != 0:
            text_arts = "\n".join(bad_list_arts)
            QMessageBox.information(
                self, "Отправка на печать", f"Нет стикеров на печать:\n{text_arts}"
            )
    except Exception as e:
        logger.error(f"Возникла ошибка при печати файла: {e}")


def print_pdf_skin(printers):
    file_list = []
    tuple_printing = tuple()
    for file in os.listdir(f"{OUTPUT_READY_FILES}"):
        if os.path.isfile(os.path.join(OUTPUT_READY_FILES, file)):
            if file.split(".")[1] == "pdf" and file.split(".")[0].strip().isdigit():
                file_path = os.path.join(OUTPUT_READY_FILES, file)
                file_list.append(file_path)

    for file, printer in zip(file_list, itertools.cycle(printers)):
        tuple_printing += ((file, printer),)

    for file_path, printer_name in tuple_printing:
        try:
            print_processes = []
            print_command = f'"{acrobat_path}" /N /T "{file_path}" "{printer_name}"'
            print_process = subprocess.Popen(print_command, shell=True)
            print_processes.append(print_process)
            logger.success(
                f"Файл {file_path} отправлен на печать на принтер {printer_name}"
            )
        except Exception as e:
            logger.error(f"Возникла ошибка при печати файла: {e}")


def print_png_images(printers):
    file_list = []
    for root, dirs, files in os.walk(OUTPUT_READY_FILES):
        for file in files:
            if file.endswith(".png"):
                file_list.append(os.path.join(root, file))

    tuple_printing = list(zip(file_list, itertools.cycle(printers)))

    for file_path, printer_name in tuple_printing:
        try:
            subprocess.run(
                ["mspaint", "/pt", file_path, printer_name, "/p:a4"], check=True
            )
            logger.success(
                f"Файл {file_path} отправлен на печать на принтер {printer_name}"
            )
        except subprocess.CalledProcessError:
            print("Ошибка при печати файла.")
