import os
from datetime import datetime

from loguru import logger
from peewee import *

from config import sticker_path_all

db = SqliteDatabase('mydatabase.db')


class GoogleTable(Model):
    name = CharField(null=True)
    folder_link = CharField(null=True)
    article = CharField(null=True)
    shop = CharField(null=True)
    status_download = BooleanField(default=False)
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
            if "под" in filename or "один" in filename or "главн" in filename:
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


if __name__ == '__main__':
    db.connect()

    # Выбор всех артикулов и перевод их в нижний регистр
    articles = [article.art.lower() for article in Article.select(Article.art)]
    print(len(articles))
    for i, record in enumerate(GoogleTable.select(), start=1):
        for art in articles:
            if art in record.article.lower():
                record.status_download = True
                record.save()
                print(f'Найден {i}{art}')
                break
        else:
            logger.error(f'Не найдены артикула {record.article}')
    db.close()