import re

import pandas as pd
import os

from loguru import logger

from config import anikoya_path, dp_path
from db import Article, GoogleTable
from utils import df_in_xlsx


def main():
    df = pd.read_excel(r'E:\значки.xlsx')
    print(df.columns)
    arts_list_in_file = df['Артикул продавца'].apply(lambda x: x.lower().strip()).tolist()
    print(len(arts_list_in_file))

    arts_list_in_db = GoogleTable.select()
    result = []
    for i in arts_list_in_db:
        arts_list = i.article.replace('\r', ' ').replace('\n', ' ').lower()
        delimiters = r'[\\/|, ]'
        substrings = re.split(delimiters, arts_list)
        arts_list = [substring.strip() for substring in substrings if substring.strip()]
        logger.debug(arts_list)
        result.extend(arts_list)

    result = list(set(result) - set(arts_list_in_file))
    print(result)
    print(len(result))
    df = pd.DataFrame(result, columns=['Артикул продавца'])
    df_in_xlsx(df, 'Не найденные артикула')
    directory = r'D:\Новая база\Скачанные файлы'
    # for i in result:
    #     os.makedirs(os.path.join(directory, i), exist_ok=True)


if __name__ == '__main__':
    main()
