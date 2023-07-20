from dataclasses import dataclass
from pprint import pprint

import pandas as pd
from loguru import logger
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from config import Article, Orders
from utils import df_in_xlsx


@dataclass
class Badge:
    art: str
    count: int
    size: int
    nums: int
    sticker_path: str
    skin_path: str
    images_paths: list


def read_excel(filename):
    df = pd.read_excel(filename,
                       usecols=['Название товара', 'Артикул Wildberries', 'Артикул продавца', 'Статус задания',
                                'Время с момента заказа']).fillna(0)
    grouped_df = df.groupby('Артикул продавца').size().reset_index(name='Количество записей')
    grouped_df['Артикул продавца'] = grouped_df['Артикул продавца'].apply(str.strip)
    sorted_df = grouped_df.sort_values(by='Количество записей', ascending=False)
    df_in_xlsx(sorted_df, 'Сгрупированный заказ')
    return sorted_df


def combine_images_to_pdf(input_files, output_pdf):
    list_images = []
    for i in input_files:
        for count in range(i.count):
            list_images.append(i)

    c = canvas.Canvas(output_pdf, pagesize=A4)
    x_offset = 20
    y_offset = 20
    img_width = (A4[0] - 2 * x_offset) / 3
    img_height = (A4[1] - 2 * y_offset) / 3 - 10

    x_positions = [x_offset, x_offset + img_width + 10, x_offset + 2 * (img_width + 10)]
    y_positions = [A4[1] - y_offset, A4[1] - y_offset - img_height - 10, A4[1] - y_offset - 2 * (img_height + 10)]

    total_images = len(list_images)
    images_per_page = 9
    num_pages = (total_images + images_per_page - 1) // images_per_page

    for page in range(num_pages):
        start_idx = page * images_per_page
        end_idx = min(start_idx + images_per_page, total_images)
        for i, img in enumerate(list_images[start_idx:end_idx]):
            x = x_positions[i % 3]
            y = y_positions[i // 3]
            c.setFont("Helvetica-Bold", 8)
            c.drawString(x, y + 2, f"#{start_idx + i + 1}     {img.art}")
            try:
                logger.success(f"Добавился скин {start_idx + i + 1}     {img.art}")
                c.drawImage(img.skin_path, x, y - img_height, width=img_width, height=img_height)
            except Exception as ex:
                logger.error(f"Не удалось добавить подложку для {img.art} {ex}")

            try:
                Orders.create(
                    num_on_list=start_idx + i + 1,
                    art=img.art,
                    nums_in_folder=img.nums,
                    size=img.size,
                    images=img.images_paths,
                    skin=img.skin_path,
                    sticker=img.sticker_path
                )
            except Exception as ex:
                logger.error(f"Записать в базу заказов {img.art} {ex}")
        c.showPage()
    c.save()


def main():
    Orders.drop_table()
    if not Orders.table_exists():
        Orders.create_table(safe=True)

    df = read_excel('заказ.xlsx')
    bad_arts = []
    order = []

    all_arts = zip(df['Артикул продавца'].tolist(), df['Количество записей'].tolist())

    for (art, count) in all_arts:
        exis = Article.get_or_none(Article.art == art)
        if exis:
            order.append(Badge(
                art=art,
                count=count,
                size=exis.size,
                nums=exis.nums_in_folder,
                sticker_path=exis.sticker,
                skin_path=exis.skin,
                images_paths=exis.images))
        else:
            bad_arts.append((art, count))

    grouped_badges = {}
    for badge in order:
        size = badge.size
        if size not in grouped_badges:
            grouped_badges[size] = []
        grouped_badges[size].append(badge)
    pprint(len(grouped_badges[56]))

    for key in grouped_badges.keys():
        print(key)
        combine_images_to_pdf(grouped_badges[key], f"output/{key}.pdf")


if __name__ == '__main__':
    main()
