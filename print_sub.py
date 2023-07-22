import itertools
import os
import subprocess
import sys

from PyQt5.QtWidgets import QMessageBox
from loguru import logger

from config import acrobat_path
from utils import FilesOnPrint


def print_pdf(file_path, num_copies, printer_name):
    # Проверка, поддерживается ли печать через subprocess на вашей платформе
    if sys.platform != 'win32':
        print("Печать PDF поддерживается только в Windows.")
    # Проверка наличия файла Adobe Acrobat Reader
    if not os.path.isfile(acrobat_path):
        print("Adobe Acrobat Reader не найден.")
        return
    try:
        print_processes = []
        # Открытие PDF-файла с использованием PyPDF2
        with open(file_path, "rb") as f:
            # Формирование команды для печати файла
            print_command = f'"{acrobat_path}" /N /T "{file_path}" "{printer_name}"'
            for _ in range(num_copies):
                # Запуск процесса печати
                print_process = subprocess.Popen(print_command, shell=True)
                print_processes.append(print_process)
        logger.success(f'Файл {file_path} отправлен на печать ({num_copies} копий). на принтер {printer_name}')
    except Exception as e:
        logger.error(f'Возникла ошибка при печати файла: {e}')



def queue(printer_list, file_list, self=None):
    """Печать постеров"""
    if self:
        self.progress_label.setText("Прогресс: 0%")
        self.progress_bar.setValue(0)
        total = len(file_list)
        completed = 0
    printer_list = [i.split('(')[0].strip() for i in printer_list]

    if len(printer_list) == 0:
        return False
    tuple_printing = tuple()
    for file, printer in zip(file_list, itertools.cycle(printer_list)):
        tuple_printing += ((file[0], file[1], printer),)
    for item in tuple_printing:
        file_path, num_copies, printer_name = item
        # print_pdf(file_path, num_copies, printer_name)
        if self:
            completed += 1
            progress = int((completed / total) * 100)
            self.progress_label.setText(f"Прогресс: {progress}%")
            self.progress_bar.setValue(progress)


def queue_sticker(printer_list, file_list, self=None):
    tuple_printing = tuple()
    count = 0

    for file, printer in zip(file_list, itertools.cycle(printer_list)):
        tuple_printing += ((file[0], file[1], printer),)
    sorted_data = sorted(tuple_printing, key=lambda x: ('-MAT' not in x[0], x[0]), reverse=True)

    for item in sorted_data:
        logger.success(item)
    for item in sorted_data:
        file_path, num_copies, printer_name = item
        # print_pdf(file_path, num_copies, printer_name)
        count += 1
        if self:
            self.progress_bar.setValue(count + 1)
            filename = file_path.split('\\')[-1]
            self.progress_label.setText(f"Печать: {filename}\nНа принтер: {printer_name}")


if __name__ == '__main__':
    printer_list = ['Fax', 'Отправить в OneNote 16']
    order = [FilesOnPrint(art='POSTER-BITVA.MATVEEVD-GLOSS-3', count=1,
                          name='Постеры Дмитрий Матвеев Чернокнижник постеры Интерьерные', status='✅'),
             FilesOnPrint(art='POSTER-BITVA.MATVEEVD-GLOSS-6', count=2,
                          name='Постеры Дмитрий Матвеев Чернокнижник постеры Интерьерные', status='✅'),
             FilesOnPrint(art='POSTER-BITVA.SHEPSOLEG-MAT-3', count=1, name='Постеры Олег Шепс постеры Интерьерные А3',
                          status='✅'), FilesOnPrint(art='POSTER-BITVA.VRAIDOS.CB2-MAT-3', count=1,
                                                    name='Постеры Виктория Райдос постеры Интерьерные А3', status='✅'),
             FilesOnPrint(art='POSTER-DEEPINS-GLOSS', count=1, name='Постеры Тиктокер Дипинс  постеры Интерьерные',
                          status='✅')]

    # file_tuple = create_file_list(order, directory=stiker_path)
    #
    # tuple_printing = queue_sticker(printer_list, file_tuple)
