import os
from datetime import datetime

import pandas as pd
from PIL import Image
from loguru import logger
from peewee import *

from config import sticker_path_all

db = SqliteDatabase('mydatabase.db')


def crop_to_content(image_path, output_path):
    start = datetime.now()
    # Открываем изображение с помощью Pillow
    image = Image.open(image_path)
    #
    # Конвертируем изображение в режим RGBA, если оно ещё не в нем
    image = image.convert("RGBA")

    # Получаем пиксельные данные изображения
    data = image.getdata()

    # Ищем границы содержимого
    left, top, right, bottom = image.width, image.height, 0, 0
    for x in range(image.width):
        for y in range(image.height):
            # Если пиксель непрозрачен (alpha > 0), обновляем границы
            if data[y * image.width + x][3] > 0:  # Пиксельный формат RGBA: (R, G, B, A)
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    # Обрезаем изображение до границ содержимого
    image_cropped = image.crop((left, top, right + 1, bottom + 1))

    # Сохраняем обрезанное изображение
    image_cropped.save(output_path)
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
        article = cls.create(art=art, folder=os.path.abspath(folder), nums=nums, size=size, shop=shop)
        article.fill_additional_columns()
        return article


    def find_skin_filename(self, folder_name):
        lower_filenames = [filename.lower() for filename in os.listdir(folder_name)]
        for filename in lower_filenames:
            if "подлож" in filename or "один" in filename or "главн" in filename:
                return filename

    def fill_additional_columns(self):
        folder_name = os.path.abspath(self.folder)
        # Заполнение столбца "Skin"
        skin_filename = self.find_skin_filename(folder_name)
        if skin_filename:
            self.skin = os.path.join(folder_name, skin_filename)

        # Заполнение столбца "Images"
        image_filenames = []


        for index, filename in enumerate(os.listdir(folder_name), start=1):
            if (filename.split('.')[0].startswith('!') or filename.split('.')[0].isdigit()) \
                    and os.path.isfile(os.path.join(folder_name, filename)):
                image_filenames.append(os.path.join(folder_name, f'{filename}'))

        self.images = ', '.join(image_filenames) if image_filenames else None
        self.nums_in_folder = len(image_filenames)

        name_sticker = self.art + '.pdf'
        sticker_file_path = None

        # Поиск файла с учетом разных регистров
        for file_name in os.listdir(sticker_path_all):
            if file_name == name_sticker or file_name.lower() == name_sticker:
                sticker_file_path = os.path.join(sticker_path_all, file_name)
                break

        self.sticker = sticker_file_path
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
    size = CharField(null=True)
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

