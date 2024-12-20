import json
import os
import shutil
import time
from io import BytesIO

import PyPDF2
import fitz
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfReader, PdfWriter
from PyQt5.QtWidgets import QMessageBox
from loguru import logger
from peewee import fn
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from created_one_pdf import created_pdfs
from db import Article, Orders, Statistic, files_base_postgresql, orders_base_postgresql, remove_russian_letters, \
    push_number
from utils import ProgressBar, df_in_xlsx

pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
Image.MAX_IMAGE_PIXELS = None


def add_header_and_footer_to_pdf(pdf_file, footer_text, A3_flag):
    """Надписи сверху пдф файла и снизу"""
    # Open the original PDF and extract its content
    with open(pdf_file, "rb") as pdf:
        pdf_content = BytesIO(pdf.read())
    if A3_flag:
        with open('Настройки\\Параметры значков_A3.json', 'r') as file:
            config = json.load(file)
        pagesize = A3
        size = 8
    else:
        with open('Настройки\\Параметры значков.json', 'r') as file:
            config = json.load(file)
        pagesize = A4
        size = 10

    x2, y2 = config['pdf down']['x'], config['pdf down']['y']
    # Load pages from the original PDF and add header and footer to each page
    reader = PdfReader(pdf_content)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        try:
            page = reader.pages[page_num]

            # Create a canvas for the page
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=pagesize)

            # Add the header text (centered) to the canvas
            can.setFont("Arial", size=size)
            if A3_flag:
                can.drawCentredString(x2, y2, f"{footer_text} - Стр.{page_num + 1}")
            else:
                can.drawCentredString(x2, y2, f"{footer_text} - Стр.{page_num + 1}")
            can.save()
            packet.seek(0)
            new_pdf = PdfReader(packet)
            page.merge_page(new_pdf.pages[0])

            writer.add_page(page)
        except Exception as ex:
            logger.error(ex)
    with open(pdf_file, "wb") as output_pdf:
        writer.write(output_pdf)


def combine_images_to_pdf(input_files, output_pdf, size=None, progress=None, self=None, A3_flag=False):
    """Создание файла с наклейками"""
    bad_skin_list = []
    x_offset = 20
    y_offset = 20
    big_list_skin = []
    for i in input_files:
        if i.nums_in_folder >= 40 or "advent" in i.art.lower():
            big_list_skin.append(i)
    input_files = [i for i in input_files if i not in big_list_skin]
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
                    logger.success(f"Добавился подложка {img.num_on_list}   {img.art}")
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
                if not os.path.exists(img.skin):
                    logger.debug(f'{img.skin} не существует')
                else:
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
                        try:
                            c.drawImage(img.skin, x - 10, y - img_height, width=img_width, height=img_height)
                        except Exception as ex:
                            logger.error(f"Не удалось добавить подложку для {img.art} {ex} 2й раз")
                            bad_skin_list.append(img.art)
            c.showPage()
        c.save()

    if big_list_skin:
        c = canvas.Canvas(f"Файлы на печать/Большие подложки {size}.pdf", pagesize=A4)
        img_width = 505
        img_height = 674
        for i, img in enumerate(big_list_skin):
            c.setFont("Helvetica-Bold", 8)
            c.drawString(30, 30, f"#{img.num_on_list}     {img.art}")
            try:
                logger.success(f"Добавился скин {img.num_on_list}     {img.art}")
                progress.update_progress()

                c.drawImage(img.skin, 40, 100, width=img_width, height=img_height)
            except Exception as ex:
                logger.error(f"Не удалось добавить подложку для {img.art} {ex}")
            c.showPage()
        c.save()
    add_header_and_footer_to_pdf(output_pdf, self.name_doc, A3_flag=A3_flag)
    return bad_skin_list


def write_images_art(image, text1):
    """Нанесения номера на значке"""
    width, height = image.size
    draw = ImageDraw.Draw(image)

    # Calculate the font size based on the image width
    font_size = int(width / 13)
    font = ImageFont.truetype("arial.ttf", font_size)

    # Добавляем надпись в правый верхний угол
    bbox1 = draw.textbbox((0, 0), text1, font=font)
    x1 = width - bbox1[2] - 5
    y1 = 5
    draw.text((x1, y1), text1, font=font, fill="black")

    return image


def write_images_art2(image, text, x, y):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 40)

    draw.text((x, y), text, font=font, fill="black")

    return image


def distribute_images(queryset, size, a3_flag, self, count) -> tuple:
    if a3_flag:
        with open('Настройки\\Параметры значков_A3.json', 'r') as file:
            config = json.load(file)
    else:
        with open('Настройки\\Параметры значков.json', 'r') as file:
            config = json.load(file)
    nums = config[f'{str(size)}']['nums']
    list_arts = [[None, i.nums_in_folder, i.images, i.id] for i in queryset]
    list_arts = sorted(list_arts, key=lambda x: x[1], reverse=True)
    # Список для хранения наборов
    sets_of_orders = []

    current_set = []  # Текущий набор
    current_count = 0  # Текущее количество элементов в наборе
    while len(list_arts) > 0:
        for order in list_arts[:]:
            if order[1] > nums:
                image_list = [(i, count) for i in order[2].split(', ')]
                if (current_count + (len(image_list) % nums)) <= nums and ((len(image_list) % nums) != 0):
                    current_set.extend(image_list[-(order[1] % nums):])
                    current_count += len(image_list) % nums
                    full_lists = order[1] // nums
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[nums * i:nums * i + nums])
                    push_number(order[3], count)
                    list_arts.remove(order)
                    count += 1
                elif (order[1] > nums) and current_count == 0:
                    full_lists = order[1] // nums
                    for i in range(full_lists):
                        sets_of_orders.append(image_list[nums * i:nums * i + nums])
                    if order[1] % nums != 0:
                        current_set.extend(image_list[-(order[1] % nums):])
                    push_number(order[3], count)
                    list_arts.remove(order)
                    count += 1
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
                    push_number(order[3], count)
                    list_arts.remove(order)
                    count += 1

            if (current_count + order[1]) <= nums:
                current_set.extend([[i, count] for i in order[2].split(', ')])
                current_count += order[1]
                list_arts.remove(order)
                push_number(order[3], count)
                count += 1
                if current_count == nums:
                    sets_of_orders.append(current_set)
                    current_set = []
                    current_count = 0
                    break
            continue
        if current_count != 0:
            sets_of_orders.append(current_set)
        if len(list_arts) == 1:
            sets_of_orders.append([[i, count] for i in list_arts[0][2].split(', ')])
            push_number(list_arts[0][3], count)
            list_arts.remove(list_arts[0])
            count += 1

        if list_arts:
            current_set = []
            current_set.extend([[i, count] for i in list_arts[0][2].split(', ')])
            current_count = list_arts[0][1]
            push_number(list_arts[0][3], count)
            list_arts.remove(list_arts[0])
            count += 1

    logger.info(f'Сумма значков: {sum([len(i) for i in sets_of_orders])}')
    # logger.info(f'Сумма значков на листах: {set([len(i) for i in sets_of_orders])}')
    logger.info(f'Количество листов: {len(sets_of_orders)}')
    if self:
        self.list_on_print += len(sets_of_orders)
    return sets_of_orders, count


def create_contact_sheet(images=None, size=None, self=None, A3_flag=False, popsocket=False):
    border_color = (0, 0, 0, 255)  # Черный цвет рамки
    border_width = 1  # Ширина рамки в пикселях
    ready_path = 'Файлы на печать'
    if A3_flag:
        a4_width = 3508
        a4_height = 4961
        with open('Настройки\\Параметры значков_A3.json', 'r') as file:
            config = json.load(file)
    else:
        a4_width = 2480
        a4_height = 3508
        with open('Настройки\\Параметры значков.json', 'r') as file:
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
            contact_sheet = Image.new('RGBA', (a4_width, a4_height), (255, 255, 255, 0))
            draw = ImageDraw.Draw(contact_sheet)

            for i in range(config[f'{str(size)}']['ICONS_PER_COL']):
                for j in range(config[f'{str(size)}']['ICONS_PER_ROW']):
                    try:
                        image = Image.open(img[i * config[f'{str(size)}']['ICONS_PER_ROW'] + j][0].strip())
                        image = write_images_art(image,
                                                 f'#{img[i * config[f"{str(size)}"]["ICONS_PER_ROW"] + j][1]}')
                        image = image.resize((image_width, image_height), Image.LANCZOS)
                    except Exception as ex:
                        break
                    try:
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
                    except Exception as ex:
                        break
                    try:
                        circle_center = ((border_rect[0] + border_rect[2]) // 2, (border_rect[1] + border_rect[3]) // 2)
                        circle_radius = min((border_rect[2] - border_rect[0]) // 2,
                                            (border_rect[3] - border_rect[1]) // 2)
                        draw.ellipse((circle_center[0] - circle_radius, circle_center[1] - circle_radius,
                                      circle_center[0] + circle_radius, circle_center[1] + circle_radius),
                                     outline=border_color, width=border_width)
                    except Exception as ex:
                        break
            if self:
                progress.update_progress()
            if not popsocket:
                path_ready = f'{ready_path}/{size}/{index}.png'
            else:
                path_ready = f'{ready_path}/Popsockets/{index}.png'
            x = config['number on badge']['x'] - 40
            y = config['number on badge']['y']
            image = write_images_art2(contact_sheet, f"{self.name_doc} Стр.{index}", x, y)
            image.save(path_ready)
            logger.success(f'Создано изображение {index}.png')

        except Exception as ex:
            logger.error(ex)
            logger.error(img)


# def merge_pdfs_stickers(queryset, output_path):
#     pdf_writer = PyPDF2.PdfWriter()
#     input_paths = [i.sticker for i in queryset if i.sticker]
#     if not input_paths:
#         return
#     for index, input_path in enumerate(input_paths, start=1):
#         try:
#             with open(input_path, 'rb') as pdf_file:
#                 pdf_reader = PyPDF2.PdfReader(pdf_file)
#
#                 # Add all pages from PdfReader to PdfWriter
#                 for page in pdf_reader.pages:
#                     pdf_writer.add_page(page)
#         except Exception:
#             pass
#     current_output_path = f"{output_path}.pdf"
#     with open(current_output_path, 'wb') as output_file:
#         pdf_writer.write(output_file)
#     PyPDF2.PdfWriter()

def merge_pdfs_stickers(queryset, output_path):
    pdf_writer = fitz.open()  # Создаем новый PDF
    input_paths = [i.sticker for i in queryset if i.sticker]
    for input_path in input_paths:
        try:
            pdf_reader = fitz.open(input_path)  # Открываем PDF
            pdf_writer.insert_pdf(pdf_reader)  # Вставляем страницы
            pdf_reader.close()  # Закрываем PDF
        except Exception as e:
            print(f"Error processing {input_path}: {e}")

    pdf_writer.save(f"{output_path}.pdf")  # Сохраняем итоговый PDF
    pdf_writer.close()  # Закрываем итоговый PDF


def created_good_images(all_arts, self, A3_flag=False):
    progress = None
    bad_skin_list = None

    try:
        ready_path = 'Файлы на печать'
        Orders.drop_table()
        if not Orders.table_exists():
            Orders.create_table(safe=True)
        bad_arts_stickers = []
        try:
            shutil.rmtree(ready_path, ignore_errors=True)
            time.sleep(1)
        except:
            pass
        os.makedirs(f'{ready_path}\\25', exist_ok=True)
        os.makedirs(f'{ready_path}\\37', exist_ok=True)
        os.makedirs(f'{ready_path}\\44', exist_ok=True)
        os.makedirs(f'{ready_path}\\56', exist_ok=True)
        os.makedirs(f'{ready_path}\\Popsockets', exist_ok=True)

        for art in all_arts:
            art_clean = remove_russian_letters(art.art.upper())
            row = Article.get_or_none(fn.UPPER(Article.art) == art_clean)
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

        # Присваивание номера записям Orders
        sorted_orders = Orders.sorted_records()
        for index, row in enumerate(sorted_orders, start=1):
            try:
                if not os.path.exists(row.folder):
                    logger.error(f'Папка не найдена {row.folder}')
                    row.delete_instance()
            except Exception as ex:
                logger.error(ex)
                row.delete_instance()

            try:
                if not os.path.exists(row.sticker):
                    logger.error(f'Стикер  не найден {row.sticker}')
                    row.sticker = None
                    row.save()
            except Exception as ex:
                logger.error(ex)
            if not row.sticker:
                bad_arts_stickers.append((row.art, row.size))

        # # Запись ненайденных артикулов и с отсутсвующих стикеров в файл
        # if bad_arts_stickers:
        #     try:
        #         df_bad_sticker = pd.DataFrame(bad_arts_stickers, columns=['Артикул', 'Размер'])
        #         df_in_xlsx(df_bad_sticker, 'Не найденные ШК в заказе')
        #     except Exception as ex:
        #         logger.error(ex)

        records = Orders.select(Orders.size).where(Orders.shop != 'Popsocket').order_by('-size').distinct()
        records = sorted([i.size for i in records])
        count = 1
        for size in records:
            queryset = Orders.select().where(Orders.size == size).where(Orders.shop != 'Popsocket')

            sets_of_orders, count = distribute_images(queryset, size, A3_flag, self, count)
            if self:
                self.progress_bar.setValue(0)
                self.progress_label.setText(f"Прогресс: Создание подложек {size} mm.")

                progress = ProgressBar(queryset.count(), self)

            try:
                logger.debug(f'Создание наклеек {size}')
                bad_skin_list = combine_images_to_pdf(queryset.order_by(Orders.num_on_list),
                                                      f"{ready_path}/Наклейки {size}.pdf", size, progress, self,
                                                      A3_flag)
            except Exception as ex:
                logger.error(ex)
                logger.error(f'Не удалось создать файл с наклейками {size}')

            try:
                logger.debug(f'Создание файла ШК {size}')
                merge_pdfs_stickers(queryset.order_by(Orders.num_on_list), f'Файлы на печать\\ШК {size}')
            except Exception as ex:
                logger.error(ex)
                logger.error(f'Не удалось создать файл ШК {size}, возможно не одного не найденно')

            try:
                logger.debug(f'Создание листов со значками {size}')
                create_contact_sheet(sets_of_orders, size, self, A3_flag)
            except Exception as ex:
                logger.error(ex)

        if bad_skin_list:
            for item in bad_skin_list:
                if Article.delete_by_art(item):
                    logger.warning("Запись и соответствующая папка успешно удалены.")
                else:
                    logger.warning("Не удалось удалить запись или папку.")
        # Popsockets
        queryset = Orders.select().where(Orders.shop == 'Popsocket')
        if len(queryset) > 0:
            size = 44
            sets_of_orders, count = distribute_images(queryset, size, A3_flag, self, count)
            if self:
                self.progress_bar.setValue(0)
                self.progress_label.setText(f"Прогресс: Создание подложек Popsocket")
                progress = ProgressBar(queryset.count(), self)

            try:
                logger.debug(f'Создание наклеек Popsocket {size}')
                bad_skin_list = combine_images_to_pdf(queryset.order_by(Orders.num_on_list),
                                                      f"{ready_path}\\Наклейки Popsockets.pdf", size, progress, self,
                                                      A3_flag)
            except Exception as ex:
                logger.error(ex)
                logger.error(f'Не удалось создать файл с наклейками {size}')

            try:
                logger.debug(f'Создание файла ШК Popsocket')
                merge_pdfs_stickers(queryset.order_by(Orders.num_on_list), f'Файлы на печать\\ШК Popsocket')
            except Exception as ex:
                logger.error(ex)
                logger.error(f'Не удалось создать файл ШК Popsocket, возможно не одного не найденно')

            try:
                logger.debug(f'Создание листов со значками Popsocket')
                create_contact_sheet(sets_of_orders, size, self, A3_flag, popsocket=True)
            except Exception as ex:
                logger.error(ex)

        if bad_skin_list:
            for item in bad_skin_list:
                if Article.delete_by_art(item):
                    logger.warning("Запись и соответствующая папка успешно удалены.")
                else:
                    logger.warning("Не удалось удалить запись или папку.")

        if self.create_pdf_checkbox.checkState() == 2:
            try:
                created_pdfs(self)
            except Exception as ex:
                logger.error(ex)

        lists = 0
        # try:
        #     lists = files_base_postgresql(self)
        # except Exception as ex:
        #     logger.error(ex)

        # try:
        #     orders_base_postgresql(self, lists)
        # except Exception as ex:
        #     logger.error(ex)

        self.list_on_print = 0
        QMessageBox.information(self, 'Завершено', 'Создание файлов завершено!')

        records = Orders.select()
        for record in records:
            record.lists = lists
            record.save()
            Statistic.create(art=record.art, nums=record.nums_in_folder, size=record.size)
    except Exception as ex:
        logger.error(ex)


if __name__ == '__main__':
    input_file = r'E:\Очередь на печать\49.png'
    output_file = r'E:\Очередь на печать\!1.png'
    # crop_to_content2(input_file, output_file)
