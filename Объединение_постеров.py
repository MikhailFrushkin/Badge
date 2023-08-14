import glob
import io
import math
import os
import tempfile

import PyPDF2
import fitz
import pandas as pd
from PIL import Image
from loguru import logger
from reportlab.lib.pagesizes import A3
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from tqdm import tqdm


def compression_pdf(pdf_file_path, output_pdf_path):
    pdf_document = fitz.open(pdf_file_path)
    # Параметры сжатия изображений
    image_compression_quality = 100  # Уровень качества JPEG
    # Создаем новый PDF-документ
    output_pdf = canvas.Canvas(output_pdf_path, pagesize=A3)
    # Размеры страницы A3
    a3_width, a3_height = A3
    # Обходим страницы PDF
    for page_num in tqdm(range(pdf_document.page_count), desc="Обработка страниц", unit="стр"):
        page = pdf_document[page_num]
        img_list = page.get_images(full=True)

        # Создаем новую страницу (кроме первой)
        if page_num != 0:
            output_pdf.showPage()

        # Обходим изображения на странице
        for img_index, img in enumerate(img_list):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            img_data = base_image["image"]

            # Сжимаем и сохраняем изображение
            img_pil = Image.open(io.BytesIO(img_data))
            img_pil.save('temp_img.jpg', format='JPEG', quality=image_compression_quality)

            # Загружаем изображение с помощью ReportLab
            img_width, img_height = img_pil.size

            # Рассчитываем размеры и координаты для вставки изображения на странице A3
            if img_width > a3_width or img_height > a3_height:
                img_width, img_height = a3_width, a3_height
            x_pos = (a3_width - img_width) / 2
            y_pos = (a3_height - img_height) / 2

            pdf_image = ImageReader('temp_img.jpg')

            # Вставляем изображение на текущую страницу
            output_pdf.drawImage(pdf_image, x_pos, y_pos, width=img_width, height=img_height)

            # Удаляем временное изображение
            img_pil.close()

    # Закрываем PDF-документ
    output_pdf.save()

    # Закрываем исходный PDF
    pdf_document.close()

    print("Готово!")


def merge_pdfs(input_paths, output_path):
    pdf_writer = PyPDF2.PdfWriter()
    # Calculate the number of groups needed based on the maximum of 10 elements per group
    count = 60
    num_groups = math.ceil(len(input_paths) / count)

    for group_index in range(num_groups):
        start_index = group_index * count
        end_index = (group_index + 1) * count

        # Get the paths for the current group
        current_group_paths = input_paths[start_index:end_index]

        for index, input_path in enumerate(current_group_paths, start=1):
            print(index, input_path)
            with open(input_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                # Add all pages from PdfReader to PdfWriter
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)

        # Write the merged pages to the output file with an index
        current_output_path = f"{output_path}_{group_index + 1}.pdf"
        with open(current_output_path, 'wb') as output_file:
            pdf_writer.write(output_file)

        # Clear the PdfWriter for the next group
        pdf_writer = PyPDF2.PdfWriter()


def one_pdf(folder_path, filename):
    pdf_filename = fr'E:\Новая база\сделать\\{filename}.pdf'
    if os.path.exists(pdf_filename):
        logger.debug(f'Файл существует: {pdf_filename}')
    else:
        poster_files = glob.glob(f"{folder_path}/*.png") + glob.glob(f"{folder_path}/*.jpg")
        poster_files = sorted(poster_files)
        good_files = []
        for file in poster_files:
            good_files.append(file)
        c = canvas.Canvas(pdf_filename, pagesize=A3)
        for i, poster_file in enumerate(good_files):
            logger.debug(poster_file)
            image = Image.open(poster_file)
            width, height = image.size
            if width > height:
                rotated_image = image.rotate(90, expand=True)
                try:
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        rotated_image.save(temp_file.name, format='JPEG')
                        c.drawImage(temp_file.name, 0, 0, width=A3[0], height=A3[1])
                except Exception as ex:
                    logger.error(ex)
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        rotated_image.save(temp_file.name, format='PNG')
                        c.drawImage(temp_file.name, 0, 0, width=A3[0], height=A3[1])
            else:
                c.drawImage(poster_file, 0, 0, width=A3[0], height=A3[1])
            if i != len(poster_files) - 1:
                c.showPage()
        c.save()
        logger.success(f'Создан файл: {pdf_filename}')


def find_files_in_directory(directory_path, file_list):
    found_files = []
    not_found_files = []
    for file_name in file_list:
        file_path = os.path.join(directory_path, file_name)
        if os.path.exists(file_path):
            found_files.append(file_path)
        else:
            not_found_files.append(file_name)

    return found_files, not_found_files


def find_intersection(list1, list2):
    return list(set(list1) & set(list2))


def main(filename):
    target_directory = r"E:\Новая база\Готовые pdf"
    df = pd.read_excel(filename)
    df['Артикул продавца'] = df['Артикул продавца'].apply(lambda x: x.lower() + '.pdf')
    art_list2 = df['Артикул продавца'].to_list()
    # art_list_gloss = [i for i in art_list2 if
    #                   '-gloss.' in i or '-gloss-' in i or '-glos' in i or '-clos' in i or '-glouss' in i]
    # art_list_mat = [i for i in art_list2 if '-mat.' in i or '-mat-' in i]
    #
    # intersection = find_intersection(art_list_gloss, art_list_mat)
    # logger.error(intersection)
    #
    # found_files_gloss, not_found_files = find_files_in_directory(target_directory, art_list_gloss)
    # print("\nФайлы не найдены:")
    # for file_name in not_found_files:
    #     print(file_name.replace('.pdf', ''))
    # print(f'Длина найденных артикулов {len(found_files_gloss)}')
    # print(f'Длина не найденных артикулов {len(not_found_files)}')
    #
    # found_files_mat, not_found_files = find_files_in_directory(target_directory, art_list_mat)
    #
    # print("\nФайлы не найдены:")
    # for file_name in not_found_files:
    #     print(file_name.replace('.pdf', ''))
    # print(f'Длина найденных артикулов {len(found_files_mat)}')
    # print(f'Длина не найденных артикулов {len(not_found_files)}')

    # output_path_gloss = r'E:\Новая база\8 раз на печать (артикула по 80шт)'
    # merge_pdfs(found_files_gloss, output_path_gloss)
    #
    # output_path_mat = r'E:\Новая база\финсиб13 matt'
    # merge_pdfs(found_files_mat, output_path_mat)
    #
    # miss_arts = set(art_list2) - set(art_list_gloss) - set(art_list_mat)
    # print(miss_arts)

    found_files_all, not_found_files = find_files_in_directory(target_directory, art_list2)
    print("\nФайлы не найдены:")
    for file_name in not_found_files:
        print(file_name.replace('.pdf', ''))
    print(f'Длина найденных артикулов {len(found_files_all)}')
    print(f'Длина не найденных артикулов {len(not_found_files)}')

    file_new_name = filename.split("\\")[-1]
    output_path_gloss = rf'E:\Новая база\{file_new_name}'
    merge_pdfs(found_files_all, output_path_gloss)


if __name__ == '__main__':
    # # Сканирование артикулов из заказа и показ ненайденных
    #
    # main(r'C:\Users\Михаил\Downloads\ПОСТЕРЫ 175 ЗАКАЗ4.xlsx')
    #
    # # Объеденение изображений в pdf из указанной папки
    # #
    # directory = r'E:\Новая база\сделать'
    # for i in os.listdir(directory):
    #     one_pdf(folder_path=os.path.join(directory, i), filename=i)

    directory = r'E:\Новая база\Готовые pdf'
    output_directory = r'E:\Новая база\E:\Новая база\Готовые pdf сжатые'
    for index, file in enumerate(os.listdir(directory)):
        compression_pdf(pdf_file_path=os.path.join(directory, file),
                        output_pdf_path=os.path.join(output_directory, file))
