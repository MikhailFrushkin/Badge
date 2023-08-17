import PyPDF2
import pandas as pd
import os
from db import Article
from utils import df_in_xlsx
from Объединение_постеров import compression_pdf


def main():
    df = pd.read_excel(r'C:\Users\Михаил\Desktop\значки.xlsx')
    df_art_list = df['Артикул продавца'].apply(lambda x: x.strip()).tolist()
    print(len(df_art_list))

    rows_arts = [i.art for i in Article.select(Article.art).where(Article.shop == 'DP')]
    diff_arts = sorted([i for i in df_art_list if i not in rows_arts])
    print(diff_arts)
    print(len(diff_arts))

    df = pd.DataFrame(diff_arts, columns=['Артикул'])
    df_in_xlsx(df, 'DP неанйденные артикула')


if __name__ == '__main__':
    # main()
    # directory = r'E:\Новая база значков\Сделать'
    # df = pd.read_excel('DP неанйденные артикула.xlsx')
    # arts = df['Артикул'].tolist()
    # for i in arts:
    #     os.makedirs(os.path.join(directory, i), exist_ok=True)

    # directory = r'E:\Новая база\Ready pdf compress'
    # list_arts = []
    # for file in os.listdir(directory):
    #     try:
    #         list_arts.append('.'.join(file.split('.')[:-1]))
    #     except:
    #         print(file)
    #
    # df = pd.DataFrame(list_arts, columns=['Артикул продавца'])
    # df_in_xlsx(df, '1233')

    # directory = r'E:\Новая база\сделать'
    # ou_directory = r'E:\Новая база\Ready pdf compress'
    # for file in os.listdir(directory):
    #     compression_pdf(pdf_file_path=os.path.join(directory, file),
    #                     output_pdf_path=os.path.join(ou_directory, file))
    #
    directory = r'E:\Новая база\сделать'
    out_directory = r'E:\Новая база\Ready pdf compress'
    with open('проблемные пдф.txt', 'r') as f:
        data = f.read()
    paths = data.replace('Ready pdf compress', 'Готовые pdf').split('\n')
    for i in paths:
        if os.path.exists(i):
            print(i)
            filename = i.split('\\')[-1]
            print(filename)
            compression_pdf(pdf_file_path=i,
                            output_pdf_path=os.path.join(out_directory, filename))