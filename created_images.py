import json
import json
import math
import os
import shutil
import time
from io import BytesIO

import PyPDF2
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfReader, PdfWriter
from PyQt5.QtWidgets import QMessageBox
from loguru import logger
from peewee import fn
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.pdfgen import canvas

from db import Article, Orders, Statistic
from utils import ProgressBar, df_in_xlsx


def add_header_and_footer_to_pdf(pdf_file, footer_text, A3_flag):
    # Open the original PDF and extract its content
    with open(pdf_file, "rb") as pdf:
        pdf_content = BytesIO(pdf.read())
    if A3_flag:
        with open('Параметры значков_A3.json', 'r') as file:
            config = json.load(file)
        pagesize = A3
        size = 8
    else:
        with open('Параметры значков.json', 'r') as file:
            config = json.load(file)
        pagesize = A4
        size = 10

    x2, y2 = config['pdf down']['x'], config['pdf down']['y']
    # Load pages from the original PDF and add header and footer to each page
    reader = PdfReader(pdf_content)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]

        # Create a canvas for the page
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=pagesize)

        # Add the header text (centered) to the canvas
        can.setFont("Helvetica", size=size)
        if A3_flag:
            can.drawCentredString(x2, y2, f"{footer_text} - Page.{page_num + 1}")
        else:
            can.drawCentredString(x2, y2, f"{footer_text} - Page.{page_num + 1}")
        can.save()
        packet.seek(0)
        new_pdf = PdfReader(packet)
        page.merge_page(new_pdf.pages[0])

        writer.add_page(page)

    with open(pdf_file, "wb") as output_pdf:
        writer.write(output_pdf)


def combine_images_to_pdf(input_files, output_pdf, progress=None, self=None, A3_flag=False):
    x_offset = 20
    y_offset = 20
    if A3_flag:
        c = canvas.Canvas(output_pdf, pagesize=landscape(A3), pageCompression=1)
        img_width = (A4[0] - 2 * x_offset) / 3
        img_height = (A4[1] - 2 * y_offset) / 3 - 10

        x_positions = [
            x_offset, x_offset + img_width + 10, x_offset + 2 * (img_width + 10),
                      x_offset + 3 * (img_width + 10), x_offset + 4 * (img_width + 10), x_offset + 5 * (img_width + 10)
        ]
        y_positions = [
            A3[0] - y_offset, A3[0] - y_offset - img_height - 15, A3[0] - y_offset - 2 * (img_height + 15)
        ]

        total_images = len(input_files)
        images_per_page = 18  # Размещаем 18 изображений на одной странице
        num_pages = (total_images + images_per_page - 1) // images_per_page

        for page in range(num_pages):
            start_idx = page * images_per_page
            end_idx = min(start_idx + images_per_page, total_images)
            for i, img in enumerate(input_files[start_idx:end_idx]):
                x = x_positions[i % 6]
                y = y_positions[i // 6]
                c.setFont("Helvetica-Bold", 6)
                c.drawString(x, y + 1, f"#{img.num_on_list}  {img.art}")
                try:
                    logger.success(f"Добавился скин {img.num_on_list}   {img.art}")
                    progress.update_progress()
                    c.drawImage(img.skin, x - 10, y - img_height - 5, width=img_width, height=img_height)
                except Exception as ex:
                    logger.error(f"Не удалось добавить подложку для {img.art} {ex}")
            c.showPage()

        c.save()
    else:
        c = canvas.Canvas(output_pdf, pagesize=A4)
        img_width = (A4[0] - 2 * x_offset) / 3
        img_height = (A4[1] - 2 * y_offset) / 3 - 5

        x_positions = [x_offset, x_offset + img_width + 5, x_offset + 2 * (img_width + 5)]
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
                    progress.update_progress()
                    c.drawImage(img.skin, x - 10, y - img_height, width=img_width, height=img_height)
                except Exception as ex:
                    logger.error(f"Не удалось добавить подложку для {img.art} {ex}")
            c.showPage()
        c.save()

    add_header_and_footer_to_pdf(output_pdf, self.name_doc, A3_flag=A3_flag)


def write_images_art(image, text1):
    width, height = image.size
    draw = ImageDraw.Draw(image)

    # Calculate the font size based on the image width
    font_size = int(width / 11)
    font = ImageFont.truetype("arial.ttf", font_size)

    # Добавляем надпись в правый верхний угол
    bbox1 = draw.textbbox((0, 0), text1, font=font)
    x1 = width - bbox1[2] - 5
    y1 = 5
    draw.text((x1, y1), text1, font=font, fill="black")

    return image


def write_images_art2(image, text, x, y):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 50)

    draw.text((x, y), text, font=font, fill="black")

    return image


def distribute_images(queryset, size, A3_flag):
    if A3_flag:
        with open('Параметры значков_A3.json', 'r') as file:
            config = json.load(file)
    else:
        with open('Параметры значков.json', 'r') as file:
            config = json.load(file)
    nums = config[f'{str(size)}']['nums']
    list_arts = [(i.num_on_list, i.nums_in_folder, i.images) for i in queryset]
    list_arts = sorted(list_arts, key=lambda x: x[1], reverse=True)

    # Список для хранения наборов
    sets_of_orders = []

    current_set = []  # Текущий набор
    current_count = 0  # Текущее количество элементов в наборе
    count = 0
    while len(list_arts) > 0:
        for order in list_arts[:]:
            if order[1] > nums:
                image_list = [(i, order[0]) for i in order[2].split(',')]
                if (current_count + (len(image_list) % nums)) <= nums and ((len(image_list) % nums) != 0):
                    current_set.extend(image_list[-(order[1] % nums):])
                    current_count += len(image_list) % nums
                    full_lists = order[1] // nums
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[nums * i:nums * i + nums])
                    list_arts.remove(order)
                elif (order[1] > nums) and current_count == 0:
                    full_lists = order[1] // nums
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[nums * i:nums * i + nums])
                    if order[1] % nums != 0:
                        current_set.extend(image_list[-(order[1] % nums):])
                    list_arts.remove(order)
                else:
                    sets_of_orders.append(current_set)
                    current_set = []
                    current_count = 0
                    full_lists = order[1] // nums
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[nums * i:nums * i + nums])

                    if order[1] % nums != 0:
                        current_set.extend(image_list[-(order[1] % nums):])
                        current_count += len(image_list[-(order[1] % nums):])
                    list_arts.remove(order)

            if (current_count + order[1]) <= nums:
                count += 1
                current_set.extend([(i, order[0]) for i in order[2].split(',')])
                current_count += order[1]
                list_arts.remove(order)
                if current_count == nums:
                    sets_of_orders.append(current_set)
                    current_set = []
                    current_count = 0
                    break
            continue
        if current_count != 0:
            sets_of_orders.append(current_set)
        if len(list_arts) == 1:
            sets_of_orders.append([(i, list_arts[0][0]) for i in list_arts[0][2].split(',')])
            list_arts.remove(list_arts[0])
        if list_arts:
            current_set = []
            current_set.extend([(i, list_arts[0][0]) for i in list_arts[0][2].split(',')])
            current_count = list_arts[0][1]
            list_arts.remove(list_arts[0])

    logger.info(f'Сумма значков: {sum([len(i) for i in sets_of_orders])}')
    logger.info(f'Сумма значков на листах: {set([len(i) for i in sets_of_orders])}')
    logger.info(f'Количество листов: {len(sets_of_orders)}')
    return sets_of_orders


def create_contact_sheet(images=None, size=None, self=None, A3_flag=False):
    border_color = (0, 0, 0, 255)  # Черный цвет рамки
    border_width = 1  # Ширина рамки в пикселях
    ready_path = 'Файлы на печать'
    if A3_flag:
        a4_width = 3508
        a4_height = 4961
        with open('Параметры значков_A3.json', 'r') as file:
            config = json.load(file)
    else:
        a4_width = 2480
        a4_height = 3508
        with open('Параметры значков.json', 'r') as file:
            config = json.load(file)
    image_width_mm = config[f'{str(size)}']['diameter']
    image_height_mm = config[f'{str(size)}']['diameter']

    # Convert mm to inches (1 inch = 25.4 mm)
    mm_to_inch = 25.4
    image_width = int(image_width_mm * 300 / mm_to_inch)
    image_height = int(image_height_mm * 300 / mm_to_inch)

    if self:
        self.progress_label.setText(f"Прогресс: Создание изображений {size} mm.")
        self.progress_bar.setValue(0)
        progress = ProgressBar(len(images), self)
    for index, img in enumerate(images, start=1):
        try:
            # Создаем пустой контейнер для объединения изображений (RGBA mode)
            contact_sheet = Image.new('RGBA', (a4_width, a4_height), (255, 255, 255, 0))  # 0 alpha for transparency
            draw = ImageDraw.Draw(contact_sheet)
            # Добавление рамки вокруг изображения

            # Итерируемся по всем изображениям и размещаем их на листе
            for i in range(config[f'{str(size)}']['ICONS_PER_COL']):
                for j in range(config[f'{str(size)}']['ICONS_PER_ROW']):
                    try:
                        image = Image.open(img[i * config[f'{str(size)}']['ICONS_PER_ROW'] + j][0].strip())
                        image = write_images_art(image, f'#{img[i * config[f"{str(size)}"]["ICONS_PER_ROW"] + j][1]}')
                        image = image.resize((image_width, image_height), Image.LANCZOS)

                        if size == 56:
                            contact_sheet.paste(image, (j * image_width - 10, i * image_height + 10 * (i + 1)))
                            border_rect = [j * image_width - 10, i * image_height + 10 * (i + 1),
                                           (j + 1) * image_width - 10, (i + 1) * image_height + 10 * (i + 1)]
                        elif size == 25 or size == 44:
                            contact_sheet.paste(image, (j * image_width + 100, i * image_height + 10 * (i + 1)))
                            border_rect = [j * image_width + 100, i * image_height + 10 * (i + 1),
                                           (j + 1) * image_width + 100, (i + 1) * image_height + 10 * (i + 1)]
                        else:
                            contact_sheet.paste(image, (j * image_width + 10, i * image_height + 10 * (i + 1)))
                            border_rect = [j * image_width + 10, i * image_height + 10 * (i + 1),
                                           (j + 1) * image_width + 10, (i + 1) * image_height + 10 * (i + 1)]
                        # Параметры круга
                        circle_center = ((border_rect[0] + border_rect[2]) // 2, (border_rect[1] + border_rect[3]) // 2)
                        circle_radius = min((border_rect[2] - border_rect[0]) // 2,
                                            (border_rect[3] - border_rect[1]) // 2)
                        draw.ellipse((circle_center[0] - circle_radius, circle_center[1] - circle_radius,
                                      circle_center[0] + circle_radius, circle_center[1] + circle_radius),
                                     outline=border_color, width=border_width)
                        # draw.rectangle(border_rect, outline=border_color, width=border_width)

                    except IndexError as ex:
                        pass

            progress.update_progress()
            contact_sheet.save(f'{ready_path}/{size}/{index}.png')
            image = Image.open(f"{ready_path}/{size}/{index}.png")
            x = config['number on badge']['x']
            y = config['number on badge']['y']
            image = write_images_art2(image, f"{self.name_doc} Стр.{index}", x, y)
            image.save(f'{ready_path}/{size}/{index}.png')
            logger.success(f'Создано изображение {index}.png')

        except Exception as ex:
            logger.error(ex)


def merge_pdfs_stickers(queryset, output_path):
    pdf_writer = PyPDF2.PdfWriter()
    input_paths = [i.sticker for i in queryset if i.sticker]
    print(input_paths)
    for index, input_path in enumerate(input_paths, start=1):
        try:
            with open(input_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)

                # Add all pages from PdfReader to PdfWriter
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
        except Exception:
            pass
    current_output_path = f"{output_path}.pdf"
    with open(current_output_path, 'wb') as output_file:
        pdf_writer.write(output_file)
    PyPDF2.PdfWriter()


def created_good_images(all_arts, self, A3_flag=False):
    try:
        ready_path = 'Файлы на печать'
        Orders.drop_table()
        if not Orders.table_exists():
            Orders.create_table(safe=True)
        bad_arts = []
        bad_arts_stickers = []
        try:
            shutil.rmtree(ready_path, ignore_errors=True)
            time.sleep(1)
        except:
            pass
        try:
            os.makedirs(f'{ready_path}\\25', exist_ok=True)
            os.makedirs(f'{ready_path}\\37', exist_ok=True)
            os.makedirs(f'{ready_path}\\44', exist_ok=True)
            os.makedirs(f'{ready_path}\\56', exist_ok=True)
        except:
            pass

        for art in all_arts:
            row = Article.get_or_none(Article.art == art.art)
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
                        ] * art.count
                Orders.bulk_create([Orders(**item) for item in data])
        sorted_orders = Orders.sorted_records()
        for index, row in enumerate(sorted_orders, start=1):
            row.num_on_list = index
            row.save()
            if not row.sticker:
                bad_arts_stickers.append((row.art, row.size))
                print((row.art, row.size))

        # Запись ненайденных артикулов и с отсутсвующих стикеров в файл
        try:
            df_bad_sticker = pd.DataFrame(bad_arts_stickers, columns=['Артикул', 'Размер'])
            df_in_xlsx(df_bad_sticker, 'Не найденные стикеры в заказе')
        except Exception as ex:
            logger.error(ex)

        records = Orders.select(Orders.size).order_by('-size').distinct()
        records = sorted([i.size for i in records])

        for size in records:
            queryset = Orders.select().where(Orders.size == size)
            for row in queryset:
                if not os.path.exists(row.folder):
                    logger.error(f'Папка не найдена {row.folder}')
                    row.delete_instance()
            if self:
                self.progress_bar.setValue(0)
                self.progress_label.setText(f"Прогресс: Создание подложек {size} mm.")

                progress = ProgressBar(queryset.count(), self)

            try:
                logger.debug(f'Создание наклейки {size}')
                combine_images_to_pdf(queryset, f"{ready_path}/{size}.pdf",
                                      progress, self, A3_flag)
            except Exception as ex:
                logger.error(ex)
                logger.error(f'Не удалось создать файл наклейнки {size}')

            try:
                logger.debug(f'Создание файла ШК {size}')
                merge_pdfs_stickers(queryset, f'Файлы на печать\\{size}ШК')
            except Exception as ex:
                logger.error(ex)
                logger.error(f'Не удалось создать файл ШК {size}, возможно не одного не найденно')

            sum_result = Orders.select(fn.SUM(Orders.nums_in_folder)).where(Orders.size == size).scalar()
            logger.info(f"Сумма значений в столбце: {sum_result}")

            sets_of_orders = distribute_images(queryset, size, A3_flag)
            try:
                logger.debug(f'Создание листов со значками {size}')
                create_contact_sheet(sets_of_orders, size, self, A3_flag)
            except Exception as ex:
                logger.error(ex)
        QMessageBox.information(self, 'Завершено', 'Создание файлов завершено!')

        records = Orders.select()
        for record in records:
            Statistic.create(art=record.art, nums=record.nums_in_folder, size=record.size)
    except Exception as ex:
        logger.error(ex)


if __name__ == '__main__':
    input_file = r'E:\Очередь на печать\49.png'
    output_file = r'E:\Очередь на печать\!1.png'
    # crop_to_content2(input_file, output_file)
