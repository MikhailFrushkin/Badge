import json
import json
import os
import shutil
import time
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfReader, PdfWriter
from PyQt5.QtWidgets import QMessageBox
from loguru import logger
from peewee import fn
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from db import Article, Orders, Statistic
from utils import ProgressBar


def add_header_and_footer_to_pdf(pdf_file, footer_text):
    # Open the original PDF and extract its content
    with open(pdf_file, "rb") as pdf:
        pdf_content = BytesIO(pdf.read())

    # Load pages from the original PDF and add header and footer to each page
    reader = PdfReader(pdf_content)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]

        # Create a canvas for the page
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=A4)

        # Add the header text (centered) to the canvas
        can.setFont("Helvetica", 12)
        width, height = A4
        can.drawCentredString(width - 90, height - 20, f"{footer_text} - Page {page_num + 1}")
        can.drawCentredString(width - 90, height - 827, f"{footer_text} - Page {page_num + 1}")

        # Save the canvas to the packet and reset it
        can.save()
        packet.seek(0)

        # Merge the packet (header) into the page
        new_pdf = PdfReader(packet)
        page.merge_page(new_pdf.pages[0])

        writer.add_page(page)

    with open(pdf_file, "wb") as output_pdf:
        writer.write(output_pdf)


def combine_images_to_pdf(input_files, output_pdf, progress=None, self=None):
    c = canvas.Canvas(output_pdf, pagesize=A4)
    x_offset = 20
    y_offset = 35
    img_width = (A4[0] - 2 * x_offset) / 3
    img_height = (A4[1] - 2 * y_offset) / 3 - 5

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
                progress.update_progress()
                c.drawImage(img.skin, x - 10, y - img_height, width=img_width, height=img_height)
            except Exception as ex:
                logger.error(f"Не удалось добавить подложку для {img.art} {ex}")
        c.showPage()
    c.save()

    add_header_and_footer_to_pdf(output_pdf, self.name_doc)


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


def write_images_art2(image, text):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 50)
    x = 1900
    y = 3450
    draw.text((x, y), text, font=font, fill="black")

    return image


def distribute_images(queryset, size_images_param):
    nums = size_images_param['nums']
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

    logger.debug(f'Сумма значков: {sum([len(i) for i in sets_of_orders])}')
    logger.debug(f'Сумма значков на листах: {set([len(i) for i in sets_of_orders])}')
    logger.debug(f'Количество листов: {len(sets_of_orders)}')
    return sets_of_orders


def create_contact_sheet(images=None, size_images_param=None, size=None, self=None):
    ready_path = 'Файлы на печать'
    a4_width = 2480
    a4_height = 3508
    image_width_mm = size_images_param['diameter']
    image_height_mm = size_images_param['diameter']

    # Convert mm to inches (1 inch = 25.4 mm)
    mm_to_inch = 25.4
    image_width = int(image_width_mm * 300 / mm_to_inch)
    image_height = int(image_height_mm * 300 / mm_to_inch)

    # Create a font for page numbers
    font_size = 30  # Adjust the font size as needed
    font = ImageFont.truetype("arial.ttf", font_size)

    if self:
        self.progress_label.setText(f"Прогресс: Создание изображений {size} mm.")
        self.progress_bar.setValue(0)
        progress = ProgressBar(len(images), self)

    for index, img in enumerate(images, start=1):
        try:
            # Создаем пустой контейнер для объединения изображений (RGBA mode)
            contact_sheet = Image.new('RGBA', (a4_width, a4_height), (255, 255, 255, 0))  # 0 alpha for transparency
            draw = ImageDraw.Draw(contact_sheet)

            # Итерируемся по всем изображениям и размещаем их на листе
            for i in range(size_images_param['ICONS_PER_COL']):
                for j in range(size_images_param['ICONS_PER_ROW']):
                    try:
                        image = Image.open(img[i * size_images_param['ICONS_PER_ROW'] + j][0].strip())
                        image = write_images_art(image, f'#{img[i * size_images_param["ICONS_PER_ROW"] + j][1]}')
                        image = image.resize((image_width, image_height), Image.LANCZOS)
                        if size == 56:
                            contact_sheet.paste(image, (j * image_width - 10, i * image_height + 10 * i))
                        else:
                            contact_sheet.paste(image, (j * image_width, i * image_height + 10 * i))

                    except IndexError as ex:
                        pass

            logger.success(f'Создано изображение {index}.png')
            progress.update_progress()
            contact_sheet.save(f'{ready_path}/{size}/{index}.png')
            image = Image.open(f"{ready_path}/{size}/{index}.png")
            image = write_images_art2(image, f"{self.name_doc} Page {index}")
            image.save(f'{ready_path}/{size}/{index}.png')
        except Exception as ex:
            logger.error(ex)


def creared_good_images(all_arts, self):
    with open('Параметры значков.json', 'r') as file:
        dict_sizes_images = json.load(file)
    try:
        ready_path2 = 'Файлы на печать'
        Orders.drop_table()
        if not Orders.table_exists():
            Orders.create_table(safe=True)
        bad_arts = []
        try:
            shutil.rmtree(ready_path2, ignore_errors=True)
            time.sleep(1)
        except:
            pass
        try:
            os.makedirs(f'{ready_path2}\\25', exist_ok=True)
            os.makedirs(f'{ready_path2}\\37', exist_ok=True)
            os.makedirs(f'{ready_path2}\\44', exist_ok=True)
            os.makedirs(f'{ready_path2}\\56', exist_ok=True)
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
            else:
                bad_arts.append((art.count, art.count))

        sorted_orders = Orders.sorted_records()
        for index, row in enumerate(sorted_orders, start=1):
            row.num_on_list = index
            row.save()

        records = Orders.select(Orders.size).order_by('-size').distinct()
        records = sorted([i.size for i in records])

        for size in records:
            if self:
                self.progress_bar.setValue(0)
                self.progress_label.setText(f"Прогресс: Создание подложек {size} mm.")

                progress = ProgressBar(Orders.select().where(Orders.size == size).count(), self)

            size_images_param = dict_sizes_images[str(size)]

            combine_images_to_pdf(Orders.select().where(Orders.size == size), f"{ready_path2}/{size}.pdf",
                                  progress, self)
            sum_result = Orders.select(fn.SUM(Orders.nums_in_folder)).where(Orders.size == size).scalar()

            logger.debug(f"Сумма значений в столбце: {sum_result}")

            sets_of_orders = distribute_images(Orders.select().where(Orders.size == size), size_images_param)
            create_contact_sheet(sets_of_orders, size_images_param, size, self)
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
