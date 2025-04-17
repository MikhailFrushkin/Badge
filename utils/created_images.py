"""
Модуль для обработки изображений и генерации PDF-файлов для системы печати значков и стикеров.

Основные функции:
- Создание монтажных листов для печати
- Генерация PDF с наклейками
- Добавление служебной информации на изображения
- Оптимизация размещения элементов на листах
"""

import json
import os
import shutil
import time
from io import BytesIO

import fitz  # Для работы с PDF (PyMuPDF)
from PIL import Image, ImageDraw, ImageFont  # Для обработки изображений
from PyPDF2 import PdfReader, PdfWriter  # Для работы с PDF
from PyQt5.QtWidgets import QMessageBox  # Для GUI сообщений
from loguru import logger  # Логирование
from peewee import fn  # ORM запросы
from reportlab.lib.pagesizes import A4, A3, landscape  # Размеры страниц
from reportlab.pdfbase import pdfmetrics  # Шрифты в PDF
from reportlab.pdfbase.ttfonts import TTFont  # Шрифты в PDF
from reportlab.pdfgen import canvas  # Генерация PDF

# Импорт моделей БД и вспомогательных функций
from base.db import push_number, Orders, Article, Statistic
from config import OUTPUT_READY_FILES
from utils.created_one_pdf import created_pdfs
from utils.utils import ProgressBar, remove_russian_letters

# Регистрация шрифта для использования в PDF
pdfmetrics.registerFont(TTFont("Arial", "arial.ttf"))

# Убираем ограничение на размер обрабатываемых изображений
Image.MAX_IMAGE_PIXELS = None


def add_header_and_footer_to_pdf(pdf_file, footer_text, A3_flag):
    """
    Добавляет верхние и нижние колонтитулы в PDF файл.

    Параметры:
        pdf_file (str): Путь к PDF файлу для модификации
        footer_text (str): Текст для отображения в нижнем колонтитуле
        A3_flag (bool): Флаг формата страницы (True - A3, False - A4)

    Возвращает:
        None: Функция модифицирует переданный файл напрямую
    """
    try:
        # Чтение исходного PDF файла
        with open(pdf_file, "rb") as pdf:
            pdf_content = BytesIO(pdf.read())

        # Выбор конфигурации в зависимости от формата
        config_path = ("Настройки\\Параметры значков_A3.json" if A3_flag
                       else "Настройки\\Параметры значков.json")
        pagesize = A3 if A3_flag else A4
        font_size = 8 if A3_flag else 10

        with open(config_path, "r", encoding='utf-8') as file:
            config = json.load(file)

        # Получение координат для размещения текста
        x_pos, y_pos = config["pdf down"]["x"], config["pdf down"]["y"]

        # Подготовка объектов для работы с PDF
        reader = PdfReader(pdf_content)
        writer = PdfWriter()

        # Обработка каждой страницы документа
        for page_num in range(len(reader.pages)):
            try:
                page = reader.pages[page_num]

                # Создание нового контента с колонтитулами
                packet = BytesIO()
                can = canvas.Canvas(packet, pagesize=pagesize)

                # Настройка шрифта и добавление текста
                can.setFont("Arial", size=font_size)
                footer = f"{footer_text} - Стр.{page_num + 1}"
                can.drawCentredString(x_pos, y_pos, footer)
                can.save()

                # Объединение с исходной страницей
                packet.seek(0)
                new_pdf = PdfReader(packet)
                page.merge_page(new_pdf.pages[0])
                writer.add_page(page)
            except Exception as ex:
                logger.error(f"Ошибка обработки страницы {page_num}: {ex}")
                continue

        # Сохранение модифицированного PDF
        with open(pdf_file, "wb") as output_pdf:
            writer.write(output_pdf)

    except Exception as ex:
        logger.error(f"Критическая ошибка в add_header_and_footer_to_pdf: {ex}")
        raise


def combine_images_to_pdf(input_files, output_pdf, size=None, progress=None, self=None, A3_flag=False):
    """
    Создает PDF файл с наклейками из набора изображений.

    Параметры:
        input_files (list): Список объектов с данными изображений
        output_pdf (str): Путь для сохранения результирующего PDF
        size (int, optional): Размер значков в мм
        progress (object, optional): Объект для отображения прогресса
        self (object, optional): Ссылка на родительское окно GUI
        A3_flag (bool, optional): Флаг формата A3

    Возвращает:
        list: Список артикулов с проблемными изображениями
    """
    bad_skin_list = []
    try:
        # Базовые отступы от краев листа
        x_offset, y_offset = 20, 20

        # Разделение изображений на обычные и большие
        big_list_skin = [
            i for i in input_files
            if i.nums_in_folder >= 40 or "advent" in i.art.lower()
        ]
        input_files = [i for i in input_files if i not in big_list_skin]

        # Настройка параметров в зависимости от формата
        if A3_flag:
            # Конфигурация для A3
            c = canvas.Canvas(output_pdf, pagesize=landscape(A3), pageCompression=1)
            img_width = (A4[0] - 2 * x_offset) / 3
            img_height = (A4[1] - 2 * y_offset) / 3 - 10
            x_positions = [x_offset + i * (img_width + 10) for i in range(6)]
            y_positions = [A3[0] - y_offset - i * (img_height + 15) for i in range(3)]
            images_per_page = 18
        else:
            # Конфигурация для A4
            c = canvas.Canvas(output_pdf, pagesize=A4)
            img_width = (A4[0] - 2 * x_offset) / 3
            img_height = (A4[1] - 2 * y_offset) / 3 - 5
            x_positions = [x_offset + i * (img_width + 5) for i in range(3)]
            y_positions = [A4[1] - y_offset - i * (img_height + 10) for i in range(3)]
            images_per_page = 9

        # Расчет количества страниц
        total_images = len(input_files)
        num_pages = (total_images + images_per_page - 1) // images_per_page

        # Генерация страниц PDF
        for page in range(num_pages):
            start_idx = page * images_per_page
            end_idx = min(start_idx + images_per_page, total_images)

            for i, img in enumerate(input_files[start_idx:end_idx]):
                x = x_positions[i % len(x_positions)]
                y = y_positions[i // len(x_positions)]

                # Добавление подписи к изображению
                font_size = 6 if A3_flag else 8
                c.setFont("Helvetica-Bold", font_size)
                c.drawString(x, y + (1 if A3_flag else 2), f"#{img.num_on_list}  {img.art}")

                # Добавление самого изображения
                try:
                    logger.success(f"Добавлена подложка {img.num_on_list} {img.art}")
                    if progress:
                        progress.update_progress()

                    c.drawImage(
                        img.skin,
                        x - 10,
                        y - img_height - (5 if A3_flag else 0),
                        width=img_width,
                        height=img_height,
                    )
                except Exception as ex:
                    logger.error(f"Ошибка добавления подложки {img.art}: {ex}")
                    bad_skin_list.append(img.art)

            c.showPage()

        c.save()

        # Обработка больших изображений (отдельный файл)
        if big_list_skin:
            try:
                big_output = f"{OUTPUT_READY_FILES}/Большие подложки {size}.pdf"
                c = canvas.Canvas(big_output, pagesize=A4)
                img_width, img_height = 505, 674

                for i, img in enumerate(big_list_skin):
                    try:
                        c.setFont("Helvetica-Bold", 8)
                        c.drawString(30, 30, f"#{img.num_on_list} {img.art}")

                        if progress:
                            progress.update_progress()

                        c.drawImage(img.skin, 40, 100, width=img_width, height=img_height)
                        c.showPage()
                    except Exception as ex:
                        logger.error(f"Ошибка большой подложки {img.art}: {ex}")

                c.save()
            except Exception as ex:
                logger.error(f"Ошибка создания файла больших подложек: {ex}")

        # Добавление колонтитулов в итоговый PDF
        if self and hasattr(self, 'name_doc'):
            add_header_and_footer_to_pdf(output_pdf, self.name_doc, A3_flag=A3_flag)

    except Exception as ex:
        logger.error(f"Критическая ошибка в combine_images_to_pdf: {ex}")
        if self:
            QMessageBox.critical(self, "Ошибка", "Ошибка при создании PDF с наклейками")
        raise

    return bad_skin_list


def write_images_art(image, text1):
    """
    Добавляет текстовую метку на изображение.

    Параметры:
        image (PIL.Image): Объект изображения для модификации
        text1 (str): Текст для добавления

    Возвращает:
        PIL.Image: Модифицированное изображение с текстом
    """
    try:
        width, height = image.size
        draw = ImageDraw.Draw(image)

        # Автоматический расчет размера шрифта
        font_size = int(width / 13)
        font = ImageFont.truetype("arial.ttf", font_size)

        # Расчет позиции текста (правый верхний угол)
        bbox = draw.textbbox((0, 0), text1, font=font)
        x = width - bbox[2] - 5  # Отступ 5 пикселей от правого края
        y = 5  # Отступ 5 пикселей от верхнего края

        # Добавление текста на изображение
        draw.text((x, y), text1, font=font, fill="black")

        return image
    except Exception as ex:
        logger.error(f"Ошибка в write_images_art: {ex}")
        raise


def write_images_art2(image, text, x, y):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("arial.ttf", 40)

    draw.text((x, y), text, font=font, fill="black")

    return image


def distribute_images(queryset, size, a3_flag, self, count) -> tuple:
    """
    Оптимизирует распределение изображений по печатным листам.

    Параметры:
        queryset (peewee.QuerySet): Набор данных из БД
        size (int): Размер значков в мм
        a3_flag (bool): Флаг формата A3
        self (object): Ссылка на родительское окно
        count (int): Начальный номер для нумерации

    Возвращает:
        tuple: (Список наборов изображений, последний использованный номер)
    """
    try:
        # Загрузка конфигурации расположения
        config_path = ("Настройки\\Параметры значков_A3.json" if a3_flag
                       else "Настройки\\Параметры значков.json")
        with open(config_path, "r", encoding='utf-8') as file:
            config = json.load(file)

        nums = config[f"{str(size)}"]["nums"]
        list_arts = [[None, i.nums_in_folder, i.images, i.id] for i in queryset]
        list_arts = sorted(list_arts, key=lambda x: x[1], reverse=True)

        sets_of_orders = []  # Итоговые наборы изображений
        current_set = []  # Текущий формируемый набор
        current_count = 0  # Количество изображений в текущем наборе

        # Алгоритм оптимального распределения
        while len(list_arts) > 0:
            for order in list_arts[:]:
                # Обработка заказов с количеством больше стандартного
                if order[1] > nums:
                    image_list = [(i, count) for i in order[2].split(", ")]

                    # Добавление остатка к текущему набору
                    if (current_count + (len(image_list) % nums)) <= nums and (
                            (len(image_list) % nums) != 0
                    ):
                        current_set.extend(image_list[-(order[1] % nums):])
                        current_count += len(image_list) % nums

                        # Добавление полных наборов
                        full_lists = order[1] // nums
                        for i in range(full_lists):
                            sets_of_orders.append(image_list[nums * i: nums * i + nums])

                        push_number(order[3], count)
                        list_arts.remove(order)
                        count += 1

                    # Обработка случая, когда текущий набор пуст
                    elif (order[1] > nums) and current_count == 0:
                        full_lists = order[1] // nums
                        for i in range(full_lists):
                            sets_of_orders.append(image_list[nums * i: nums * i + nums])

                        if order[1] % nums != 0:
                            current_set.extend(image_list[-(order[1] % nums):])

                        push_number(order[3], count)
                        list_arts.remove(order)
                        count += 1

                    # Обработка общего случая
                    else:
                        sets_of_orders.append(current_set)
                        current_set = []
                        current_count = 0
                        full_lists = order[1] // nums

                        for i in range(full_lists):
                            sets_of_orders.append(image_list[nums * i: nums * i + nums])

                        if order[1] % nums != 0:
                            current_set.extend(image_list[-(order[1] % nums):])
                            current_count += len(image_list[-(order[1] % nums):])

                        push_number(order[3], count)
                        list_arts.remove(order)
                        count += 1

                # Добавление к текущему набору, если есть место
                if (current_count + order[1]) <= nums:
                    current_set.extend([[i, count] for i in order[2].split(", ")])
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

            # Добавление оставшегося набора
            if current_count != 0:
                sets_of_orders.append(current_set)

            # Обработка последнего элемента
            if len(list_arts) == 1:
                sets_of_orders.append([[i, count] for i in list_arts[0][2].split(", ")])
                push_number(list_arts[0][3], count)
                list_arts.remove(list_arts[0])
                count += 1

            # Начало нового набора, если остались элементы
            if list_arts:
                current_set = []
                current_set.extend([[i, count] for i in list_arts[0][2].split(", ")])
                current_count = list_arts[0][1]
                push_number(list_arts[0][3], count)
                list_arts.remove(list_arts[0])
                count += 1

        # Логирование статистики
        total_icons = sum([len(i) for i in sets_of_orders])
        total_sheets = len(sets_of_orders)
        logger.info(f"Сумма значков: {total_icons}")
        logger.info(f"Количество листов: {total_sheets}")

        if self:
            self.list_on_print += total_sheets

        return sets_of_orders, count

    except Exception as ex:
        logger.error(f"Ошибка в distribute_images: {ex}")
        raise


def create_contact_sheet(images=None, size=None, self=None, A3_flag=False, popsocket=False):
    """
    Создает монтажные листы для печати значков.

    Параметры:
        images (list): Список изображений для размещения
        size (int): Размер значков в мм
        self (object): Ссылка на родительское окно
        A3_flag (bool): Флаг формата A3
        popsocket (bool): Флаг обработки popsocket-изображений
    """
    try:
        # Настройка параметров
        border_color = (0, 0, 0, 255)  # Цвет рамки (черный)
        border_width = 1  # Толщина рамки

        # Загрузка конфигурации
        config_path = ("Настройки\\Параметры значков_A3.json" if A3_flag
                       else "Настройки\\Параметры значков.json")
        with open(config_path, "r", encoding='utf-8') as file:
            config = json.load(file)

        # Установка размеров страницы
        if A3_flag:
            page_width, page_height = 3508, 4961  # Размеры A3 в пикселях (300dpi)
        else:
            page_width, page_height = 2480, 3508  # Размеры A4 в пикселях (300dpi)

        # Расчет размеров изображений
        image_width_mm = config[f"{str(size)}"]["diameter"]
        image_height_mm = config[f"{str(size)}"]["diameter"]
        mm_to_inch = 25.4  # Коэффициент перевода мм в дюймы
        image_width = int(image_width_mm * 300 / mm_to_inch)
        image_height = int(image_height_mm * 300 / mm_to_inch)

        # Настройка прогресс-бара
        if self:
            self.progress_label.setText(f"Прогресс: Создание изображений {size} mm.")
            self.progress_bar.setValue(0)
            progress = ProgressBar(len(images), self)

        # Генерация каждого монтажного листа
        for index, img in enumerate(images, start=1):
            try:
                # Создание нового изображения (листа)
                contact_sheet = Image.new("RGBA", (page_width, page_height), (255, 255, 255, 0))
                draw = ImageDraw.Draw(contact_sheet)

                # Размещение изображений на листе
                for i in range(config[f"{str(size)}"]["ICONS_PER_COL"]):
                    for j in range(config[f"{str(size)}"]["ICONS_PER_ROW"]):
                        try:
                            # Открытие и подготовка изображения
                            img_path = img[i * config[f"{str(size)}"]["ICONS_PER_ROW"] + j][0].strip()
                            image = Image.open(img_path)

                            # Добавление номера на изображение
                            num_text = f'#{img[i * config[f"{str(size)}"]["ICONS_PER_ROW"] + j][1]}'
                            image = write_images_art(image, num_text)

                            # Изменение размера изображения
                            image = image.resize((image_width, image_height), Image.LANCZOS)
                        except Exception as ex:
                            break

                        try:
                            # Позиционирование изображения на листе
                            if size == 56:
                                x = j * image_width - 10
                                y = i * image_height + 10 * (i + 1)
                            elif size in (25, 44):
                                x = j * image_width + 100
                                y = i * image_height + 10 * (i + 1)
                            else:
                                x = j * image_width + 10
                                y = i * image_height + 10 * (i + 1)

                            # Вставка изображения
                            contact_sheet.paste(image, (x, y))

                            # Рисование рамки
                            border_rect = [
                                x, y,
                                x + image_width,
                                y + image_height
                            ]

                            # Рисование круглой рамки
                            circle_center = (
                                (border_rect[0] + border_rect[2]) // 2,
                                (border_rect[1] + border_rect[3]) // 2
                            )
                            circle_radius = min(
                                (border_rect[2] - border_rect[0]) // 2,
                                (border_rect[3] - border_rect[1]) // 2
                            )
                            draw.ellipse(
                                (
                                    circle_center[0] - circle_radius,
                                    circle_center[1] - circle_radius,
                                    circle_center[0] + circle_radius,
                                    circle_center[1] + circle_radius
                                ),
                                outline=border_color,
                                width=border_width
                            )
                        except Exception as ex:
                            break

                # Обновление прогресса
                if self:
                    progress.update_progress()

                # Определение пути сохранения
                if not popsocket:
                    path_ready = f"{OUTPUT_READY_FILES}/{size}/{index}.png"
                else:
                    path_ready = f"{OUTPUT_READY_FILES}/Popsockets/{index}.png"

                # Добавление служебной информации и сохранение
                x = config["number on badge"]["x"] - 40
                y = config["number on badge"]["y"]
                info_text = f"{self.name_doc} Стр.{index}"
                image = write_images_art2(contact_sheet, info_text, x, y)
                image.save(path_ready)

                logger.success(f"Создано изображение {index}.png")

            except Exception as ex:
                logger.error(f"Ошибка создания листа {index}: {ex}")
                logger.error(f"Проблемные данные: {img}")
                continue

    except Exception as ex:
        logger.error(f"Критическая ошибка в create_contact_sheet: {ex}")
        raise


def merge_pdfs_stickers(queryset, output_path):
    """
    Объединяет несколько PDF файлов стикеров в один.

    Параметры:
        queryset (peewee.QuerySet): Набор данных из БД
        output_path (str): Путь для сохранения объединенного PDF
    """
    try:
        pdf_writer = fitz.open()  # Создание нового PDF документа

        # Получение списка файлов стикеров
        input_paths = [i.sticker for i in queryset if i.sticker]

        # Объединение файлов
        for input_path in input_paths:
            try:
                pdf_reader = fitz.open(input_path)
                pdf_writer.insert_pdf(pdf_reader)
                pdf_reader.close()
            except Exception as e:
                logger.error(f"Ошибка обработки файла {input_path}: {e}")
                continue

        # Сохранение результата
        pdf_writer.save(f"{output_path}.pdf")
        pdf_writer.close()

    except Exception as ex:
        logger.error(f"Ошибка в merge_pdfs_stickers: {ex}")
        raise


def created_good_images(all_arts, self, A3_flag=False):
    """
    Основная функция подготовки всех файлов для печати.

    Параметры:
        all_arts (list): Список всех артикулов для обработки
        self (object): Ссылка на родительское окно GUI
        A3_flag (bool): Флаг формата A3

    Возвращает:
        None: Все результаты сохраняются в файлы
    """
    progress = None
    bad_skin_list = None

    try:
        self.list_on_print = 0  # Счетчик листов

        # Подготовка базы данных
        Orders.drop_table()
        Orders.create_table(safe=True)

        # Подготовка директорий
        try:
            shutil.rmtree(OUTPUT_READY_FILES, ignore_errors=True)
            time.sleep(1)  # Пауза для завершения удаления
        except Exception as ex:
            logger.error(f"Ошибка очистки директории: {ex}")

        # Создание необходимых папок
        os.makedirs(f"{OUTPUT_READY_FILES}\\25", exist_ok=True)
        os.makedirs(f"{OUTPUT_READY_FILES}\\37", exist_ok=True)
        os.makedirs(f"{OUTPUT_READY_FILES}\\44", exist_ok=True)
        os.makedirs(f"{OUTPUT_READY_FILES}\\56", exist_ok=True)
        os.makedirs(f"{OUTPUT_READY_FILES}\\Popsockets", exist_ok=True)

        # Заполнение таблицы Orders данными
        for art in all_arts:
            try:
                art_clean = remove_russian_letters(art.art.upper())
                row = Article.get_or_none(fn.UPPER(Article.art) == art_clean)

                if row:
                    # Создание записей для каждого экземпляра артикула
                    data = [{
                        "art": row.art,
                        "folder": row.folder,
                        "nums": row.nums,
                        "nums_in_folder": row.nums_in_folder,
                        "size": row.size,
                        "skin": row.skin,
                        "sticker": row.sticker,
                        "images": row.images,
                        "shop": row.shop,
                    }] * art.count

                    Orders.bulk_create([Orders(**item) for item in data])
            except Exception as ex:
                logger.error(f"Ошибка обработки артикула {art.art}: {ex}")
                continue

        # Проверка существования файлов и папок
        bad_arts_stickers = []
        sorted_orders = Orders.sorted_records()

        for order in sorted_orders:
            try:
                # Проверка существования папки с изображениями
                if not os.path.exists(order.folder):
                    logger.error(f"Папка не найдена {order.folder}")
                    order.delete_instance()
                    continue

                # Проверка существования файла стикера
                if not os.path.exists(order.sticker):
                    logger.error(f"Стикер не найден {order.sticker}")
                    order.sticker = None
                    order.save()
                    bad_arts_stickers.append((order.art, order.size))
            except Exception as ex:
                logger.error(f"Ошибка проверки файлов для {order.art}: {ex}")
                continue

        # Обработка для каждого размера значков
        records = (
            Orders.select(Orders.size)
            .where(Orders.shop != "Popsocket")
            .order_by("-size")
            .distinct()
        )
        sizes = sorted([i.size for i in records])
        count = 1  # Счетчик для нумерации

        for size in sizes:
            try:
                # Получение данных для текущего размера
                queryset = (
                    Orders.select()
                    .where(Orders.size == size)
                    .where(Orders.shop != "Popsocket")
                )

                # Распределение изображений по листам
                sets_of_orders, count = distribute_images(
                    queryset, size, A3_flag, self, count
                )

                # Настройка прогресс-бара
                if self:
                    self.progress_bar.setValue(0)
                    self.progress_label.setText(f"Прогресс: Создание подложек {size} mm.")
                    progress = ProgressBar(queryset.count(), self)

                # Создание PDF с наклейками
                try:
                    logger.debug(f"Создание наклеек {size}")
                    bad_skin_list = combine_images_to_pdf(
                        queryset.order_by(Orders.num_on_list),
                        f"{OUTPUT_READY_FILES}/Наклейки {size}.pdf",
                        size,
                        progress,
                        self,
                        A3_flag,
                    )
                except Exception as ex:
                    logger.error(f"Ошибка создания наклеек {size}: {ex}")

                # Создание PDF со штрих-кодами
                try:
                    logger.debug(f"Создание файла ШК {size}")
                    merge_pdfs_stickers(
                        queryset.order_by(Orders.num_on_list),
                        f"{OUTPUT_READY_FILES}\\ШК {size}"
                    )
                except Exception as ex:
                    logger.error(f"Ошибка создания ШК {size}: {ex}")

                # Создание монтажных листов
                try:
                    logger.debug(f"Создание листов со значками {size}")
                    create_contact_sheet(sets_of_orders, size, self, A3_flag)
                except Exception as ex:
                    logger.error(f"Ошибка создания листов {size}: {ex}")

            except Exception as ex:
                logger.error(f"Ошибка обработки размера {size}: {ex}")
                continue

        # Удаление проблемных артикулов
        if bad_skin_list:
            for item in bad_skin_list:
                try:
                    if Article.delete_by_art(item):
                        logger.warning(f"Удален артикул {item}")
                    else:
                        logger.warning(f"Не удалось удалить артикул {item}")
                except Exception as ex:
                    logger.error(f"Ошибка удаления артикула {item}: {ex}")

        # Обработка Popsockets
        queryset = Orders.select().where(Orders.shop == "Popsocket")
        if queryset.count() > 0:
            try:
                size = 44  # Стандартный размер для Popsockets
                sets_of_orders, count = distribute_images(
                    queryset, size, A3_flag, self, count
                )

                if self:
                    self.progress_bar.setValue(0)
                    self.progress_label.setText("Прогресс: Создание подложек Popsocket")
                    progress = ProgressBar(queryset.count(), self)

                # Создание PDF с наклейками для Popsockets
                try:
                    logger.debug("Создание наклеек Popsocket")
                    bad_skin_list = combine_images_to_pdf(
                        queryset.order_by(Orders.num_on_list),
                        f"{OUTPUT_READY_FILES}\\Наклейки Popsockets.pdf",
                        size,
                        progress,
                        self,
                        A3_flag,
                    )
                except Exception as ex:
                    logger.error(f"Ошибка создания наклеек Popsocket: {ex}")

                # Создание PDF со штрих-кодами для Popsockets
                try:
                    logger.debug("Создание файла ШК Popsocket")
                    merge_pdfs_stickers(
                        queryset.order_by(Orders.num_on_list),
                        f"{OUTPUT_READY_FILES}\\ШК Popsocket"
                    )
                except Exception as ex:
                    logger.error(f"Ошибка создания ШК Popsocket: {ex}")

                # Создание монтажных листов для Popsockets
                try:
                    logger.debug("Создание листов Popsocket")
                    create_contact_sheet(
                        sets_of_orders, size, self, A3_flag, popsocket=True
                    )
                except Exception as ex:
                    logger.error(f"Ошибка создания листов Popsocket: {ex}")

            except Exception as ex:
                logger.error(f"Ошибка обработки Popsockets: {ex}")

        # Создание единого PDF (если выбрано в настройках)
        if hasattr(self, 'create_pdf_checkbox') and self.create_pdf_checkbox.checkState() == 2:
            try:
                created_pdfs(self)
            except Exception as ex:
                logger.error(f"Ошибка создания единого PDF: {ex}")

        # Сохранение статистики
        lists = 0  # Можно добавить логику подсчета листов

        records = Orders.select()
        for record in records:
            try:
                record.lists = lists
                record.save()
                Statistic.create(
                    art=record.art,
                    nums=record.nums_in_folder,
                    size=record.size
                )
            except Exception as ex:
                logger.error(f"Ошибка сохранения статистики для {record.art}: {ex}")
                continue

        # Уведомление об окончании обработки
        self.list_on_print = 0
        QMessageBox.information(self, "Завершено", "Создание файлов завершено!")

    except Exception as ex:
        logger.error(f"Критическая ошибка в created_good_images: {ex}")
        if self:
            QMessageBox.critical(self, "Ошибка", "Произошла критическая ошибка при создании файлов")
        raise
