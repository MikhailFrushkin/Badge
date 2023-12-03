import glob
import math
import os
import tempfile

import PyPDF2
import pandas as pd
from PIL import Image
from loguru import logger
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from utils import ProgressBar


def one_pdf(folder_path, pdf_file_path, progress):
    if os.path.exists(pdf_file_path):
        logger.debug(f'Файл существует: {pdf_file_path}')
    else:
        poster_files = glob.glob(f"{folder_path}/*.png") + glob.glob(f"{folder_path}/*.jpg")
        poster_files = sorted(poster_files)
        good_files = []
        for file in poster_files:
            good_files.append(file)
        c = canvas.Canvas(pdf_file_path, pagesize=A4)
        for i, poster_file in enumerate(good_files):
            if progress:
                progress.update_progress()
            image = Image.open(poster_file)
            width, height = image.size
            if width > height:
                rotated_image = image.rotate(90, expand=True)
                try:
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        rotated_image.save(temp_file.name, format='JPEG')
                        c.drawImage(temp_file.name, 0, 0, width=A4[0], height=A4[1])
                except Exception as ex:
                    logger.error(ex)
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        rotated_image.save(temp_file.name, format='PNG')
                        c.drawImage(temp_file.name, 0, 0, width=A4[0], height=A4[1])
            else:
                c.drawImage(poster_file, 0, 0, width=A4[0], height=A4[1])
            if i != len(poster_files) - 1:
                c.showPage()
        c.save()
        logger.success(f'Создан файл: {pdf_file_path}')


def created_pdfs(self=None):
    progress = None
    if self:
        self.progress_bar.setValue(0)

    ready_path = 'Файлы на печать'
    directory_list = ['25', '37', '44', '56', 'Popsockets']
    for size_dir in directory_list:
        directory = os.path.join(ready_path, size_dir)
        if os.path.exists(directory):
            len_files = len(os.listdir(directory))
            if len_files != 0:
                filename = os.path.join(directory, f'!PDF {size_dir}.pdf')
                if self:
                    self.progress_label.setText(f"Прогресс: Создание PDF файла {size_dir} mm.")
                    progress = ProgressBar(len_files, self)
                one_pdf(folder_path=directory, pdf_file_path=filename, progress=progress)


if __name__ == '__main__':
    created_pdfs()
