import os

import pandas as pd

from db import remove_russian_letters
from utils import df_in_xlsx


def main():
    df_all = pd.read_excel('E:\\значки.xlsx')
    df_all['Артикул продавца'] = df_all['Артикул продавца'].apply(lambda x: x.lower().strip())
    arts = df_all['Артикул продавца'].tolist()
    print(len(df_all))

    arts_dir = [i.replace('.pdf', '').lower().strip() for i in os.listdir(r'E:\База значков\Значки ШК')]
    print(len(arts_dir))

    result = set(map(remove_russian_letters, arts)) - set(map(remove_russian_letters, arts_dir))
    print(len(result))

    print(result)
    df = pd.DataFrame(list(map(str.upper, result)), columns=['Артикул'])
    df_in_xlsx(df, 'Отсутствуют ШК-значки')


if __name__ == '__main__':
    main()