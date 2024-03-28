import json
from pprint import pprint

import pandas as pd
import os

from loguru import logger

from config import anikoya_path, dp_path
from db import Article, remove_russian_letters
from utils import df_in_xlsx


def main():
    # df = pd.read_excel(r'D:\значки.xlsx')
    # print(df.columns)
    # arts_list_in_file = df['Артикул продавца'].apply(lambda x: remove_russian_letters(x.lower()).strip()).tolist()
    # print(len(arts_list_in_file))
    file_json = r'D:\PyCharm\mycego_online\mycego_online\files_parse\files_result\result_wb.json'
    with open(file_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    arts_list_in_file_badge = []
    arts_list_in_file_posters = []
    arts_list_in_file_kruzhka = []

    for i, value in data.items():
        i = i.lower().strip()
        if value['subjectName'] == 'Значки' and (
            'box1' not in i and 'znachki-' not in i and 'sumka-' not in i and 'boshki' not in i
        ):
            arts_list_in_file_badge.append(remove_russian_letters(i))
        elif value['subjectName'] == 'Плакаты' or value['subjectName'] == 'Постеры':
            arts_list_in_file_posters.append(i)
        elif value['subjectName'] == 'Кружки':
            arts_list_in_file_kruzhka.append(i)

    print(f'Значки: {len(arts_list_in_file_badge)}')
    print(f'Постеры: {len(arts_list_in_file_posters)}')
    print(f'Кружки: {len(arts_list_in_file_kruzhka)}')

    # Значки
    arts_list_in_db = [i.art.lower() for i in Article.select()]
    result = list(set(arts_list_in_file_badge) - set(arts_list_in_db))

    print(result)
    print(len(result))
    df = pd.DataFrame(result, columns=['Артикул продавца'])
    df_in_xlsx(df, 'Не найденные артикула')

    # directory = r'D:\Новая база\Скачанные файлы'
    # for i in result:
    #     os.makedirs(os.path.join(directory, i), exist_ok=True)


if __name__ == '__main__':
    main()
