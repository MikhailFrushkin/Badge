import os
from datetime import datetime

import pandas as pd
from PIL import Image
from loguru import logger
from peewee import *

from config import path_root, sticker_path_all

db = SqliteDatabase(f'{path_root}\mydatabase.db')


def crop_to_content(image_path, output_path):
    start = datetime.now()
    # Открываем изображение с помощью Pillow
    image = Image.open(image_path)
    #
    # # Конвертируем изображение в режим RGBA, если оно ещё не в нем
    # image = image.convert("RGBA")
    #
    # # Получаем пиксельные данные изображения
    # data = image.getdata()
    #
    # # Ищем границы содержимого
    # left, top, right, bottom = image.width, image.height, 0, 0
    # for x in range(image.width):
    #     for y in range(image.height):
    #         # Если пиксель непрозрачен (alpha > 0), обновляем границы
    #         if data[y * image.width + x][3] > 0:  # Пиксельный формат RGBA: (R, G, B, A)
    #             left = min(left, x)
    #             top = min(top, y)
    #             right = max(right, x)
    #             bottom = max(bottom, y)
    #
    # # Обрезаем изображение до границ содержимого
    # image_cropped = image.crop((left, top, right + 1, bottom + 1))
    #
    # # Сохраняем обрезанное изображение
    # image_cropped.save(output_path)
    image.save(output_path)
    logger.debug(datetime.now() - start)


class GoogleTable(Model):
    name = CharField(null=True)
    quantity = CharField(null=True)
    designer = CharField(null=True)
    date = DateField(null=True)
    folder_link = CharField(null=True)
    singles = BooleanField(null=True)
    mockups = BooleanField(null=True)
    packaging = BooleanField(null=True)
    checked_by_katya = BooleanField(null=True)
    added = BooleanField(null=True)
    performer = CharField(null=True)
    article = CharField(null=True)
    status_download = BooleanField(default=False)
    shop = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db


class Article(Model):
    art = CharField(null=True, index=True)
    folder = CharField(null=True)
    nums = IntegerField(null=True)
    nums_in_folder = IntegerField(null=True)
    size = IntegerField(null=True)
    skin = CharField(null=True)
    sticker = CharField(null=True)
    images = TextField(null=True)
    shop = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db

    def __str__(self):
        return self.art

    @classmethod
    def create_with_art(cls, art, folder, shop):
        existing_article = cls.get_or_none(art=art)
        if existing_article:
            return existing_article
        try:
            nums, size = art.split('-')[-2:]
            nums = int(nums)
            size = int(size)
        except (ValueError, IndexError):
            nums = None
            if art.endswith('56'):
                size = 56
            else:
                size = 37
        article = cls.create(art=art, folder=folder, nums=nums, size=size, shop=shop)
        article.fill_additional_columns()
        return article

    def fill_additional_columns(self):
        print(self.art)
        print(os.path.abspath(self.folder))
        folder_name = os.path.basename(self.folder)
        # Заполнение столбца "Skin"
        skin_filename = [filename for filename in os.listdir(self.folder) if "подлож" in filename.lower() or
                         "один" in filename.lower()]
        if skin_filename:
            self.skin = os.path.join(self.folder, skin_filename[0])

        # Заполнение столбца "Images"
        image_filenames = []
        for index, filename in enumerate(os.listdir(self.folder), start=1):
            if filename.split('.')[0].isdigit() and os.path.isfile(os.path.join(self.folder, filename)):
                try:
                    crop_to_content(os.path.join(self.folder, filename), os.path.join(self.folder, f'!{filename}'))
                except Exception as ex:
                    logger.error(ex)
                image_filenames.append(os.path.join(self.folder, f'{filename}'))

        for root, dirs, files in os.walk(self.folder):
            for file in files:
                if file.split('.')[0].isdigit() or file == 'Картинка1.png':
                    try:
                        os.remove(os.path.join(root, file))
                        print(f"Файл {os.path.join(root, file)} успешно удален.")
                    except OSError as ex:
                        print(f"Не удалось удалить файл {os.path.join(root, file)}: {ex}")
        # for index, filename in enumerate(os.listdir(self.folder), start=1):
        #     if filename.split('.')[0].startswith('!') and os.path.isfile(os.path.join(self.folder, filename)):
        #         image_filenames.append(os.path.join(self.folder, f'{filename}'))
        self.images = ', '.join(image_filenames) if image_filenames else None
        self.nums_in_folder = len(image_filenames)

        for root, _, files in os.walk(sticker_path_all):
            for file in files:
                if file == self.art + '.pdf':
                    self.sticker = os.path.join(root, file)

        # if len(skin_filename) != 1 or int(folder_name.split('-')[-2]) != len(image_filenames):
        #     logger.error(f"Не записался артикул в базу, т.к. не соответствует число подложек или файлов {folder_name}")
        #     return
        self.save()


class Orders(Article):
    num_on_list = IntegerField(null=True)

    class Meta:
        database = db
        ordering = ['size', 'art']

    @classmethod
    def sorted_records(cls):
        # Метод класса для получения отсортированных записей
        return cls.select().order_by(cls.size)


class Statistic(Model):
    art = CharField()
    nums = IntegerField()
    created_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db


def add_rows_google_table():
    """Запись в базу из файла excel"""
    data = pd.read_excel(r'C:\Users\Rebase_znachki\AniKoya\files\Таблица гугл Anikoya.xlsx')
    data = data[~data['Ссылка на папку'].isna() & ~data['Ссылка на папку'].isnull()
                & data['Ссылка на папку'].str.startswith('https://') &
                ~data['АРТИКУЛ ВБ'].isna() & ~data['АРТИКУЛ ВБ'].isnull()
                ]
    for _, row in data.iterrows():
        if pd.isnull(row['Дата']):
            date = None
        elif len(row['Дата']) == 10:
            date = datetime.strptime(row['Дата'], '%d.%m.%Y').date()
        elif len(row['Дата']) == 8:
            date = datetime.strptime(row['Дата'], '%d.%m.%y').date()
        else:
            date = None
        record = GoogleTable(
            name=row['Наименование'],
            quantity=row['Количество'],
            designer=row['Дизайнер'],
            date=date,
            folder_link=row['Ссылка на папку'],
            singles=bool(row['Одиночки']) if not pd.isnull(row['Одиночки']) else None,
            mockups=bool(row['Мокапы']) if not pd.isnull(row['Мокапы']) else None,
            packaging=bool(row['Упаковка']) if not pd.isnull(row['Упаковка']) else None,
            checked_by_katya=bool(row['Проверено Катей']) if not pd.isnull(row['Проверено Катей']) else None,
            added=bool(row['Заведено']) if not pd.isnull(row['Заведено']) else None,
            performer=row['Исполнитель (загрузка на вб)'],
            article=row['АРТИКУЛ ВБ']
        )
        record.save()


def add_record_google_table(name, quantity, designer, date, folder_link, singles,
                            mockups, packaging, checked_by_katya, added, performer, article, shop):
    """Добавление записи в таблицу с гугла"""
    if pd.isnull(date):
        date = None
    elif len(date) == 10:
        date = datetime.strptime(date, '%d.%m.%Y').date()
    elif len(date) == 8:
        date = datetime.strptime(date, '%d.%m.%y').date()
    else:
        date = None
    record, created = GoogleTable.get_or_create(
        folder_link=folder_link,
        defaults={
            'name': name,
            'quantity': quantity,
            'designer': designer,
            'date': date,
            'singles': bool(singles) if not pd.isnull(singles) else None,
            'mockups': bool(mockups) if not pd.isnull(mockups) else None,
            'packaging': bool(packaging) if not pd.isnull(packaging) else None,
            'checked_by_katya': bool(checked_by_katya) if not pd.isnull(checked_by_katya) else None,
            'added': bool(added) if not pd.isnull(added) else None,
            'performer': performer,
            'article': article,
            'shop': shop
        }
    )

    if created:
        print('Новая запись добавлена:', record.name)


def print_records_by_month(month, year):
    records = GoogleTable.select().where(
        fn.strftime('%m', GoogleTable.date) == str(month).zfill(2),
        fn.strftime('%Y', GoogleTable.date) == str(year)
    )
    for record in records:
        print(record.date, record.folder_link, record.article)

    return records


db.connect()
db.create_tables([Statistic])

# Закрытие соединения с базой данных (необязательно, но рекомендуется)
db.close()

