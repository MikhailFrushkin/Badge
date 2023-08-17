import re

import pandas as pd
import os
from db import Article
from utils import df_in_xlsx
from Объединение_постеров import compression_pdf


def main():
    """Значки.Вывод отсутсвтующих артикулов в базе"""
    df = pd.read_excel(r'C:\Users\Михаил\Desktop\значки.xlsx')
    df_art_list = df['Артикул продавца'].apply(lambda x: x.strip()).tolist()
    print(len(df_art_list))

    rows_arts = [i.art for i in Article.select(Article.art).where(Article.shop == 'DP')]
    diff_arts = sorted([i for i in df_art_list if i not in rows_arts])
    print(diff_arts)
    print(len(diff_arts))

    df = pd.DataFrame(diff_arts, columns=['Артикул'])
    df_in_xlsx(df, 'DP неанйденные артикула')


def create_list_arts_in_folder():
    directory = r'E:\Новая база\Ready pdf compress'
    list_arts = []
    for file in os.listdir(directory):
        try:
            list_arts.append(('.'.join(file.split('.')[:-1])).upper())
        except:
            print(file)

    df = pd.DataFrame(list_arts, columns=['Артикул продавца'])
    df_in_xlsx(df, 'Список артикулов в папке')
    return list_arts


def create_list_arts_all():
    df = pd.read_excel(r'C:\Users\Михаил\Desktop\постеры.xlsx')
    df_art_list = df['Артикул продавца'].apply(lambda x: x.strip()).tolist()
    return df_art_list


def arts_in_google_table():
    arts_list = []
    df = pd.read_excel('Таблица гугл.xlsx', usecols=['Ссылка', 'Артикул на ВБ'])
    df['Артикул на ВБ'] = df['Артикул на ВБ'].astype(str)
    df['Артикул на ВБ'] = df['Артикул на ВБ'].apply(lambda x: re.sub(r'\s+', ' ', x))
    df['Артикул на ВБ'] = df['Артикул на ВБ'].apply(lambda x: x.replace(',', ' '))
    df['Артикул на ВБ'] = df['Артикул на ВБ'].apply(lambda x: x.replace('_x000D_', ' '))
    df['Артикул на ВБ'] = df['Артикул на ВБ'].apply(lambda x: arts_list.extend(x.split()))
    arts_list = [i for i in arts_list if i != 'nan']
    return arts_list


if __name__ == '__main__':
    # main()
    # arts_in_google = arts_in_google_table()
    all_arts = create_list_arts_all()
    arts_in_folder = create_list_arts_in_folder()

    result = sorted([i for i in all_arts if i not in arts_in_folder])
    print(len(result))
    print(result)

    directory = r'E:\Новая база\сделать'
    for i in result:
        os.makedirs(os.path.join(directory, i), exist_ok=True)

    # directory = r'E:\Новая база\сделать'
    # ou_directory = r'E:\Новая база\Ready pdf compress'
    # for file in os.listdir(directory):
    #     compression_pdf(pdf_file_path=os.path.join(directory, file),
    #                     output_pdf_path=os.path.join(ou_directory, file))

    # directory = r'E:\Новая база\сделать'
    # out_directory = r'E:\Новая база\Ready pdf compress'
    # with open('проблемные пдф.txt', 'r') as f:
    #     data = f.read()
    # paths = data.replace('Ready pdf compress', 'Готовые pdf').split('\n')
    # for i in paths:
    #     if os.path.exists(i):
    #         print(i)
    #         filename = i.split('\\')[-1]
    #         print(filename)
    #         compression_pdf(pdf_file_path=i,
    #                         output_pdf_path=os.path.join(out_directory, filename))
