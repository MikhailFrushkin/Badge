import pandas as pd
import os

from config import anikoya_path, dp_path
from db import Article
from utils import df_in_xlsx


def main():
    df = pd.read_excel(r'E:\значки.xlsx')
    print(df.columns)
    arts_list_in_file = df['Артикул продавца'].apply(lambda x: x.lower().strip()).tolist()
    print(len(arts_list_in_file))

    arts_list_in_db = [i.art.lower() for i in Article.select()]
    print(len(arts_list_in_db))

    result = list(set(arts_list_in_file) - set(arts_list_in_db))
    print(result)
    print(len(result))
    df = pd.DataFrame(result, columns=['Артикул продавца'])
    df_in_xlsx(df, 'Не найденные артикула')
    directory = r'D:\Новая база\Скачанные файлы'
    # for i in result:
    #     os.makedirs(os.path.join(directory, i), exist_ok=True)


if __name__ == '__main__':
    main()
