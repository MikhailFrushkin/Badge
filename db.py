import os
import re
from datetime import datetime

import psycopg2
from PIL import Image
from loguru import logger
from peewee import *

from config import sticker_path_all, dbname, user, password, host, machine_name

db = SqliteDatabase('mydatabase.db')


def remove_russian_letters(input_string):
    # Используем регулярное выражение для поиска всех русских букв
    russian_letters_pattern = re.compile('[а-яА-Я]')

    # Заменяем найденные русские буквы на пустую строку
    result_string = re.sub(russian_letters_pattern, '', input_string)

    return result_string.strip()


def update_base_postgresql():
    db_params = {
        "host": host,
        "database": dbname,
        "user": user,
        "password": password
    }

    arts_value = Article.select().count()

    # Создание подключения и контекстного менеджера
    with psycopg2.connect(**db_params) as connection:
        # Создание таблицы, если она не существует
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS Update_base (
            machin VARCHAR,
            update_timestamp TIMESTAMP DEFAULT current_timestamp,
            arts INT
        );
        '''
        with connection.cursor() as cursor:
            cursor.execute(create_table_query)

            cursor.execute("SELECT * FROM Update_base WHERE machin = %s;", (machine_name,))

            existing_record = cursor.fetchone()
            if existing_record:
                # Обновление существующей записи
                update_query = "UPDATE Update_base SET update_timestamp = %s, arts = %s WHERE machin = %s;"
                update_values = (datetime.now(), arts_value, machine_name)
                cursor.execute(update_query, update_values)
            else:
                # Вставка новой записи
                insert_query = "INSERT INTO Update_base (machin, update_timestamp, arts) VALUES (%s, %s, %s);"
                insert_values = (machine_name, datetime.now(), arts_value)
                cursor.execute(insert_query, insert_values)

        # Подтверждение изменений (commit) выполняется один раз
        connection.commit()


def files_base_postgresql(self):
    db_params = {
        "host": host,
        "database": dbname,
        "user": user,
        "password": password
    }
    num_lists = self.list_on_print
    # Создание подключения и контекстного менеджера
    with psycopg2.connect(**db_params) as connection:
        # Создание таблицы, если она не существует
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS files (
            machin VARCHAR,
            update_timestamp TIMESTAMP DEFAULT current_timestamp,
            name_file VARCHAR,
            found_arts INT,
            num_badges INT,
            num_lists INT
        );
        '''
        with connection.cursor() as cursor:
            cursor.execute(create_table_query)

            name_file = self.name_doc
            found_arts = Orders.select().count()
            num_badges = Orders.select(fn.SUM(Orders.nums_in_folder)).scalar()

            insert_query = ("INSERT INTO files (machin, update_timestamp, "
                            "name_file, found_arts, num_badges, num_lists) "
                            "VALUES (%s, %s, %s, %s, %s, %s);")
            insert_values = (machine_name, datetime.now(), name_file, found_arts, num_badges, num_lists)
            cursor.execute(insert_query, insert_values)

        # Подтверждение изменений (commit) выполняется один раз
        connection.commit()
    return num_lists


def orders_base_postgresql(self, lists):
    db_params = {
        "host": host,
        "database": dbname,
        "user": user,
        "password": password
    }

    # Создание подключения и контекстного менеджера
    with psycopg2.connect(**db_params) as connection:
        # Создание таблицы, если она не существует
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS orders (
            art VARCHAR,
            num INT,
            size INT, 
            machin VARCHAR,
            name_file VARCHAR,
            update_timestamp TIMESTAMP DEFAULT current_timestamp,
            num_on_list INT,
            lists INT
        );
        '''
        with connection.cursor() as cursor:
            cursor.execute(create_table_query)

            name_file = self.name_doc
            orders = []
            query = Orders.select()
            for order in query:
                art = order.art
                check_query = "SELECT COUNT(*) FROM orders WHERE art = %s AND name_file = %s;"
                cursor.execute(check_query, (art, name_file))
                count = cursor.fetchone()[0]
                if count == 0:
                    orders.append((art, order.nums_in_folder, order.size, machine_name, name_file, datetime.now(),
                                   order.num_on_list, lists))

            insert_data_query = (
                "INSERT INTO orders (art, num, size, machin, name_file, update_timestamp, num_on_list, lists)"
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);")

            cursor.executemany(insert_data_query, orders)

        connection.commit()


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
    folder_link = CharField(null=True)
    article = CharField(null=True)
    shop = CharField(null=True)
    status_download = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.now)

    def __str__(self):
        return self.name

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

    def save(self, *args, **kwargs):
        if self.art:
            self.art = str(self.art).lower()
        super(Article, self).save(*args, **kwargs)

    @classmethod
    def create_with_art(cls, art, folder, shop):
        art = remove_russian_letters(art).lower()
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
            if ("под" in filename.lower()
                    or "один" in filename.lower()
                    or "главн" in filename.lower()
                    or "nabor" in filename.lower()
                    or "one" in filename.lower()):
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
            if (filename.split('.')[0].startswith('!') or filename.split('.')[0].strip().isdigit()) \
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
    lists = IntegerField(null=True)

    class Meta:
        database = db
        ordering = ['created_at']

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


def add_record_google_table(name, folder_link, article, shop):
    """Добавление записи в таблицу с гугла"""

    record, created = GoogleTable.get_or_create(
        folder_link=folder_link,
        defaults={
            'name': name,
            'article': article,
            'shop': shop
        }
    )

    if created:
        logger.debug('Новая запись добавлена:', record.name)


if __name__ == '__main__':
    # db.connect()
    # db.create_tables([Statistic, GoogleTable, Orders, Article])
    # db.close()
    # update_base_postgresql()
    print(remove_russian_letters('Масленников_Артëм'))