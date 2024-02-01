import os
import re
from datetime import datetime
from pprint import pprint

from loguru import logger
from peewee import *

from config import sticker_path_all, dp_path, anikoya_path, all_badge

db = SqliteDatabase('mydatabase.db')


def remove_russian_letters(input_string):
    # Используем регулярное выражение для поиска всех русских букв
    russian_letters_pattern = re.compile('[а-яА-Я]')

    # Заменяем найденные русские буквы на пустую строку
    result_string = re.sub(russian_letters_pattern, '', input_string)

    return result_string.strip()


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
            if "под" in filename or "один" in filename:
                return filename

    def fill_additional_columns(self):
        folder_name = os.path.abspath(self.folder)
        # Заполнение столбца "Skin"
        skin_filename = self.find_skin_filename(folder_name)
        if skin_filename:
            self.skin = os.path.join(folder_name, skin_filename)
        # Заполнение столбца "Images"
        image_filenames = [os.path.join(folder_name, f) for f in os.listdir(folder_name)
                           if os.path.isfile(os.path.join(folder_name, f)) and
                           (f.split('.')[0].startswith('!') or f.split('.')[0].strip().isdigit())]
        self.images = ', '.join(image_filenames) if image_filenames else None
        self.nums_in_folder = len(image_filenames)

        # name_sticker = self.art + '.pdf'
        # sticker_file_path = None
        #
        # # Поиск файла с учетом разных регистров
        # for file_name in os.listdir(sticker_path_all):
        #     if file_name == name_sticker or file_name.lower() == name_sticker:
        #         sticker_file_path = os.path.abspath(os.path.join(sticker_path_all, file_name))
        #         break
        sticker_file_path = sticker_dict.get(self.art.lower(), None)

        self.sticker = sticker_file_path
        self.save()


def update_arts_db(path, shop):
    count = 0
    start = datetime.now()
    for root, dirs, files in os.walk(path):
        for dir in dirs:
            if len(dir) > 10:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), shop)
                print('\r', count, end='', flush=True)

    print('Нет подложек')
    records = Article.select().where(Article.skin >> None)
    for i in records:
        print(os.path.abspath(i.folder))

    print('Нет картинок с цифрами')
    records = Article.select().where(Article.images >> None)
    for i in records:
        print(os.path.abspath(i.folder))

    print('НЕ соответствует число картинок с базой')
    count = 0
    records = Article.select().where(Article.nums_in_folder != Article.nums)
    for i in records:
        count += 1
        print(count)
        print(os.path.abspath(i.folder))
        # if os.path.exists(os.path.abspath(i.folder)):
        #     try:
        #         subprocess.Popen(['explorer', os.path.abspath(i.folder)], shell=True)
        #     except Exception as e:
        #         print(f"Не удалось открыть папку: {e}")
        # else:
        #     print("Указанной папки не существует")
        i.nums = i.nums_in_folder
        i.save()
    logger.debug(datetime.now() - start)


if __name__ == '__main__':
    # try:
    #     with db.atomic():
    #         db.drop_tables([Article])
    # except Exception as ex:
    #     logger.error(ex)
    #
    # if not Article.table_exists():
    #     Article.create_table(safe=True)

    sticker_dict = {i.replace('.pdf', '').lower(): os.path.abspath(os.path.join(sticker_path_all, i))
                    for i in os.listdir(sticker_path_all)}
    # update_arts_db(dp_path, 'DP')
    update_arts_db(anikoya_path, 'AniKoya')
    update_arts_db(rf'{all_badge}\\Popsockets', 'Popsocket')
