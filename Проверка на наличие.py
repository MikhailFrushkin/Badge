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


def create_list_arts_in_folder(directory):
    list_arts = []
    for file in os.listdir(directory):
        try:
            if os.path.isdir(os.path.join(directory, file)):
                list_arts.append(file)
            else:
                list_arts.append(('.'.join(file.split('.')[:-1])).upper())
        except:
            print(file)

    df = pd.DataFrame(list_arts, columns=['Артикул продавца'])
    df_in_xlsx(df, 'Список артикулов в папке')
    return list_arts


def create_list_arts_all(df):

    df_art_list = df['Артикул продавца'].apply(lambda x: x.strip().upper()).tolist()
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
    directory = r'E:\Новая база\Готовые pdf'
    # directory = r'E:\База значков\DP'
    # directory = r'E:\База значков\AniKoya'

    # df = pd.read_excel(r'C:\Users\Михаил\Desktop\значки.xlsx')
    df = pd.read_excel(r'C:\Users\Михаил\Desktop\постеры.xlsx')

    # main()
    # arts_in_google = arts_in_google_table()

    all_arts = create_list_arts_all(df)
    arts_in_folder = create_list_arts_in_folder(directory)

    result = sorted([i for i in all_arts if i not in arts_in_folder])

    # result = [i for i in result if '13NEW' in i or '12NEW' in i or '11NEW' in i]
    # print(len(result))
    # print(result)

    directory = r'E:\Новая база\сделать'
    for i in result:
        os.makedirs(os.path.join(directory, i), exist_ok=True)
