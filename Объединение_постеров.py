import glob
import math
import os
import tempfile
from pprint import pprint

import PyPDF2
import pandas as pd
from PIL import Image
from google.oauth2 import service_account
from googleapiclient.discovery import build
from loguru import logger
from reportlab.lib.pagesizes import A3
from reportlab.pdfgen import canvas

from utils import df_in_xlsx


def read_table_google(CREDENTIALS_FILE='google_acc.json',
                      spreadsheet_id='1IaXufU8CYTQsMDxEvynBzlRAFm_G43Kll0PO3lvQDxA'):
    logger.debug(f'Читаю гугл таблицу')
    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
        service = build('sheets', 'v4', credentials=credentials)
        # Пример чтения файла
        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Надо сделать!B1:M30000',
        ).execute()

    except Exception as ex:
        logger.error(f'Ошибка чтения гуглтаблицы {ex}')
    data = values.get('values', [])
    headers = data[0]
    for row in data:
        missing_columns = len(headers) - len(row)
        if missing_columns > 0:
            row += [''] * missing_columns

    headers = data[0]  # Заголовки столбцов из первого элемента списка значений
    rows = data[1:]
    if len(headers) != len(rows[0]):
        pprint(headers)
        print(len(headers), len(rows[0]))

        pprint(rows[0])
        print("Ошибка: количество столбцов не совпадает с количеством значений.")
    else:
        df = pd.DataFrame(rows, columns=headers)
        df_in_xlsx(df, 'Таблица гугл')


def search_url(list_of_values):
    df = pd.read_excel('Таблица гугл.xlsx')
    df['Артикул на ВБ'] = df['Артикул на ВБ'].str.lower()
    list_of_values = [value.lower() for value in list_of_values]
    # Создайте новый столбец, в котором будет найденное значение из списка, если оно присутствует в тексте столбца "Артикул на ВБ"
    df['Найденное значение'] = df['Артикул на ВБ'].apply(
        lambda x: next((value for value in list_of_values if value in x), None))
    # Отфильтруйте строки, в которых найдено значение из списка
    filtered_df = df[df['Найденное значение'].notnull()]
    # Оставьте только столбцы "Артикул на ВБ", "Ссылка" и "Найденное значение"
    result = filtered_df[['Артикул на ВБ', 'Ссылка', 'Найденное значение']]
    # Вывод результата
    df_in_xlsx(result, 'Ссылки на скачивание')
    print(result)


def merge_pdfs(input_paths, output_path):
    pdf_writer = PyPDF2.PdfWriter()

    # Calculate the number of groups needed based on the maximum of 10 elements per group
    count = 66
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
    art_list_gloss = [i for i in art_list2 if
                      '-gloss.' in i or '-gloss-' in i or '-glos' in i or '-clos' in i or '-glouss' in i]
    art_list_mat = [i for i in art_list2 if '-mat.' in i or '-mat-' in i]

    intersection = find_intersection(art_list_gloss, art_list_mat)
    logger.error(intersection)
    found_files_gloss, not_found_files = find_files_in_directory(target_directory, art_list_gloss)

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
    miss_arts = set(art_list2) - set(art_list_gloss) - set(art_list_mat)
    print(miss_arts)

    print(art_list2)
    found_files_all, not_found_files = find_files_in_directory(target_directory, art_list2)

    print("\nФайлы не найдены:")
    for file_name in not_found_files:
        print(file_name.replace('.pdf', ''))
    print(f'Длина найденных артикулов {len(found_files_all)}')
    print(f'Длина не найденных артикулов {len(not_found_files)}')
    print(found_files_all)


if __name__ == '__main__':
    # Сканирование артикулов из заказа и показ ненайденных
    main(r'10.xlsx')

    # Объеденение изображений в pdf из указанной папки

    # directory = r'E:\Новая база\сделать'
    # for i in os.listdir(directory):
    #     one_pdf(folder_path=os.path.join(directory, i), filename=i)
