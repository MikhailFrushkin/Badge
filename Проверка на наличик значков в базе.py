import pandas as pd
import os

from config import anikoya_path, dp_path
from db import Article, remove_russian_letters
from utils import df_in_xlsx


def main():
    df = pd.read_excel(r'E:\значки.xlsx')
    print(df.columns)
    arts_list_in_file = df['Артикул продавца'].apply(lambda x: remove_russian_letters(x.lower()).strip()).tolist()
    print(len(arts_list_in_file))

    arts_list_in_db = [i.art.lower() for i in Article.select()]
    print(len(arts_list_in_db))

    result = list(set(arts_list_in_file) - set(arts_list_in_db))

    result = [i for i in result
              if ('sumka-' not in i.lower()
                  and 'box1-' not in i.lower()
                  and 'boshki-' not in i.lower()
                  # and ('11new' in i.lower() or '12new' in i.lower() or '13new' in i.lower())
                  )
              # and ('25' in i.lower() or '44' in i.lower())
              ]
    print(result)
    print(len(result))
    df = pd.DataFrame(result, columns=['Артикул продавца'])
    df_in_xlsx(df, 'Не найденные артикула')
    directory = r'D:\Новая база\Скачанные файлы'
    # for i in result:
    #     os.makedirs(os.path.join(directory, i), exist_ok=True)


if __name__ == '__main__':
    main()
