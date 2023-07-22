import glob
import os
from pprint import pprint

import pandas as pd
from loguru import logger
from peewee import fn
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from config import path_root
from db import Article, Orders
from utils import df_in_xlsx
from PIL import Image, ImageDraw, ImageFont


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
    c = canvas.Canvas(output_pdf, pagesize=A4)
    x_offset = 20
    y_offset = 20
    img_width = (A4[0] - 2 * x_offset) / 3
    img_height = (A4[1] - 2 * y_offset) / 3 - 10

    x_positions = [x_offset, x_offset + img_width + 10, x_offset + 2 * (img_width + 10)]
    y_positions = [A4[1] - y_offset, A4[1] - y_offset - img_height - 10, A4[1] - y_offset - 2 * (img_height + 10)]

    total_images = len(input_files)
    images_per_page = 9
    num_pages = (total_images + images_per_page - 1) // images_per_page

    for page in range(num_pages):
        start_idx = page * images_per_page
        end_idx = min(start_idx + images_per_page, total_images)
        for i, img in enumerate(input_files[start_idx:end_idx]):
            x = x_positions[i % 3]
            y = y_positions[i // 3]
            c.setFont("Helvetica-Bold", 8)
            c.drawString(x, y + 2, f"#{img.num_on_list}     {img.art}")
            try:
                logger.success(f"Добавился скин {img.num_on_list}     {img.art}")
                c.drawImage(img.skin, x, y - img_height, width=img_width, height=img_height)
            except Exception as ex:
                logger.error(f"Не удалось добавить подложку для {img.art} {ex}")
        c.showPage()
    c.save()


def write_images_art(image, text1):
    width, height = image.size
    draw = ImageDraw.Draw(image)

    # Calculate the font size based on the image width
    font_size = int(width / 12)
    font = ImageFont.truetype("arial.ttf", font_size)

    # Добавляем надпись в правый верхний угол
    bbox1 = draw.textbbox((0, 0), text1, font=font)
    x1 = width - bbox1[2] - 5
    y1 = 5
    draw.text((x1, y1), text1, font=font, fill="black")

    return image


def distribute_images(queryset, size):
    dict_sizes_images = {
        25: {'diameter': 35, 'nums': 48, 'ICONS_PER_ROW': 6, 'ICONS_PER_COL': 8},
        37: {'diameter': 51, 'nums': 20, 'ICONS_PER_ROW': 4, 'ICONS_PER_COL': 5},
        44: {'diameter': 53, 'nums': 15, 'ICONS_PER_ROW': 3, 'ICONS_PER_COL': 5},
        56: {'diameter': 70, 'nums': 12, 'ICONS_PER_ROW': 3, 'ICONS_PER_COL': 4}
    }
    size_images_param = dict_sizes_images[size]

    queryset = queryset.order_by('-nums_in_folder')
    list_arts = [(i.id, i.nums_in_folder, i.images) for i in queryset]
    # Список для хранения наборов
    sets_of_orders = []

    current_set = []  # Текущий набор
    current_count = 0  # Текущее количество элементов в наборе
    count = 0
    while len(list_arts) > 0:
        for order in list_arts:
            if order[1] > size_images_param['nums']:
                image_list = [(i, order[0]) for i in order[2].split(',')]
                if (current_count + (len(image_list) % size_images_param['nums'])) <= size_images_param['nums'] and (
                        (len(image_list) % size_images_param['nums']) != 0):
                    current_set.extend(image_list[-(order[1] % size_images_param['nums']):])
                    current_count += len(image_list) % size_images_param['nums']

                    logger.debug(order[1])
                    logger.debug(size_images_param['nums'])
                    logger.debug(order[1] % size_images_param['nums'])

                    full_lists = order[1] // size_images_param['nums']
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[
                                              size_images_param['nums'] * i:size_images_param['nums'] * i +
                                                                            size_images_param['nums']])
                        logger.error(image_list[
                                     size_images_param['nums'] * i:size_images_param['nums'] * i + size_images_param[
                                         'nums']])
                    list_arts.remove(order)
                elif (order[1] > size_images_param['nums']) and current_count == 0:
                    full_lists = order[1] // size_images_param['nums']
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[
                                              size_images_param['nums'] * i:size_images_param['nums'] * i +
                                                                            size_images_param['nums']])
                        logger.error((image_list[
                                      size_images_param['nums'] * i:size_images_param['nums'] * i + size_images_param[
                                          'nums']]))

                    current_set.extend(image_list[-(order[1] % size_images_param['nums']):])

                    logger.debug(order[1])
                    logger.debug(size_images_param['nums'])
                    logger.debug(order[1] % size_images_param['nums'])
                    logger.error(image_list[-(order[1] % size_images_param['nums']):])

                    list_arts.remove(order)
                else:
                    logger.debug(current_set)
                    sets_of_orders.append(current_set)
                    current_set = []
                    current_count = 0

                    full_lists = order[1] // size_images_param['nums']
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[
                                              size_images_param['nums'] * i:size_images_param['nums'] * i +
                                                                            size_images_param['nums']])
                        logger.error((image_list[
                                      size_images_param['nums'] * i:size_images_param['nums'] * i + size_images_param[
                                          'nums']]))

                    if order[1] % size_images_param['nums'] != 0:
                        current_set.extend(image_list[-(order[1] % size_images_param['nums']):])
                        current_count += len(image_list[-(order[1] % size_images_param['nums']):])
                    logger.debug(order[1])
                    logger.debug(size_images_param['nums'])
                    logger.debug(order[1] % size_images_param['nums'])

                    list_arts.remove(order)

            if (current_count + order[1]) <= size_images_param['nums']:
                count += 1
                current_set.extend([(i, order[0]) for i in order[2].split(',')])
                current_count += order[1]
                list_arts.remove(order)
                if current_count == size_images_param['nums']:
                    sets_of_orders.append(current_set)
                    logger.success(f'{current_set} , {current_count}')
                    current_set = []
                    current_count = 0
                    break
            continue
        if current_count != 0:
            sets_of_orders.append(current_set)
            logger.success(f'{current_set} , {current_count}')
        if len(list_arts) == 1:
            logger.error(list_arts)
            sets_of_orders.append([(i, list_arts[0][0]) for i in list_arts[0][2].split(',')])
            list_arts.remove(list_arts[0])
        if list_arts:
            current_set = []
            current_set.extend([(i, list_arts[0][0]) for i in list_arts[0][2].split(',')])
            current_count = list_arts[0][1]
            list_arts.remove(list_arts[0])

    print(sum([len(i) for i in sets_of_orders]))
    print(set([len(i) for i in sets_of_orders]))
    print(len(sets_of_orders))
    for sublist in sets_of_orders:
        if len(sublist) == 60:
            print(sublist)

    print(len(set([i[1] for item in sets_of_orders for i in item])))
    create_contact_sheet(sets_of_orders, size_images_param, size)


def crop_to_content(image):
    # Convert the image to grayscale
    grayscale_image = image.convert('L')

    # Get the bounding box of the non-white (content) region
    bbox = grayscale_image.getbbox()

    # Crop the image to the bounding box
    cropped_image = image.crop(bbox)

    return cropped_image


def create_contact_sheet(images=None, size_images_param=None, size=None):
    a4_width = 2480
    a4_height = 3508
    image_width_mm = size_images_param['diameter']
    image_height_mm = size_images_param['diameter']

    # Convert mm to inches (1 inch = 25.4 mm)
    mm_to_inch = 25.4
    image_width = int(image_width_mm * 300 / mm_to_inch)
    image_height = int(image_height_mm * 300 / mm_to_inch)
    for index, img in enumerate(images, start=1):
        try:
            # Создаем пустой контейнер для объединения изображений (RGBA mode)
            contact_sheet = Image.new('RGBA', (a4_width, a4_height), (255, 255, 255, 0))  # 0 alpha for transparency
            # Итерируемся по всем изображениям и размещаем их на листе
            for i in range(size_images_param['ICONS_PER_COL']):
                for j in range(size_images_param['ICONS_PER_ROW']):
                    try:
                        image = Image.open(img[i * size_images_param['ICONS_PER_ROW'] + j][0].strip())
                        cropped_image = crop_to_content(image)
                        image = write_images_art(cropped_image, f'#{img[i * size_images_param["ICONS_PER_ROW"] + j][1]}')
                        image = image.resize((image_width, image_height), Image.LANCZOS)
                        contact_sheet.paste(image, (j * image_width, i * image_height))
                    except IndexError as ex:
                        logger.error(img[0][1])
            logger.success(f'Созданно изображение {index}.png')
            contact_sheet.save(f'output/{size}/{index}.png')
        except Exception as ex:
            logger.error(ex)


def main(filename='заказ.xlsx'):
    Orders.drop_table()
    if not Orders.table_exists():
        Orders.create_table(safe=True)

    df = read_excel(filename)
    bad_arts = []

    all_arts = zip(df['Артикул продавца'].tolist(), df['Количество записей'].tolist())

    for (art, count) in all_arts:
        row = Article.get_or_none(Article.art == art)
        if row:
            data = [{'art': row.art,
                     'folder': row.folder,
                     'nums': row.nums,
                     'nums_in_folder': row.nums_in_folder,
                     'size': row.size,
                     'skin': row.skin,
                     'sticker': row.sticker,
                     'images': row.images,
                     'shop': row.shop,
                     }
                    ] * count
            Orders.bulk_create([Orders(**item) for item in data])
        else:
            bad_arts.append((art, count))

    sorted_orders = Orders.sorted_records()
    for index, row in enumerate(sorted_orders, start=1):
        row.num_on_list = index
        row.save()

    records = Orders.select(Orders.size).distinct()
    for size in records:
        combine_images_to_pdf(Orders.select().where(Orders.size == size.size), f"output/{size.size}.pdf")
        sum_result = Orders.select(fn.SUM(Orders.nums_in_folder)).where(Orders.size == size).scalar()

        print("Сумма значений в столбце:", sum_result)
        distribute_images(Orders.select().where(Orders.size == size.size), size.size)



if __name__ == '__main__':
    main()
