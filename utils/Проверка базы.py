import os
import re
import shutil
import time
from datetime import datetime

from loguru import logger
from peewee import *

from config import sticker_path_all, brands_paths, bad_list, all_badge

db = SqliteDatabase('base/mydatabase.db')


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
        if '(' in art or ')' in art:
            shutil.rmtree(os.path.abspath(folder))
        if existing_article:
            return existing_article
        try:
            nums, size = art.split('-')[-2:]
            nums = int(nums)
            size = int(size)
        except (ValueError, IndexError):
            if '11new' in art or '12new' in art or '13new' in art or '14new' in art or '15new' in art:
                logger.error(art)
                logger.error(os.path.abspath(folder))
                shutil.rmtree(os.path.abspath(folder))
                return
            nums = None
            if art.endswith('56'):
                size = 56
            elif art.endswith('25'):
                size = 25
            elif 'Popsockets' in folder:
                size = 44
            else:
                size = 37
        article = cls.create(art=art, folder=os.path.abspath(folder), nums=nums, size=size, shop=shop)
        article.fill_additional_columns()
        return article

    def fill_additional_columns(self):
        art = self.art.strip().lower()
        image_filenames = []
        folder_name = os.path.abspath(self.folder)
        file_list = os.listdir(folder_name)
        for file in file_list:
            if "под" in file.lower() or "один" in file.lower():
                skin_path = os.path.join(folder_name, file)
                self.skin = os.path.abspath(skin_path)
                break
        else:
            logger.error(f'Не найдена подложка {art} {folder_name}')
            logger.error(f'Удален {art}')
            self.delete_instance()
            shutil.rmtree(self.folder)
            return

        for file in file_list:
            file_name = file.split('.')[0].strip().replace('!', '')
            file_path = os.path.join(folder_name, file)
            if os.path.isfile(file_path) and file_name.isdigit():
                image_filenames.append(file_path)

        self.images = ', '.join(image_filenames) if image_filenames else None

        self.nums_in_folder = len(image_filenames)

        sticker_file_path = sticker_dict.get(art, None)

        self.sticker = sticker_file_path
        self.save()


def update_arts_db(path, shop):
    global count
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                if dir not in ignore_dirs:
                    count += 1
                    Article.create_with_art(dir, os.path.join(root, dir), shop)
                    # print('\r', count, end='', flush=True)
                    print(dir)


def check_bd():
    bad_list_new = []
    logger.debug('Нет подложек')
    records = Article.select().where(Article.skin >> None)
    for i in records:
        logger.info(os.path.abspath(i.folder))

    logger.debug('Нет картинок с цифрами')
    records = Article.select().where(Article.images >> None)
    for i in records:
        logger.info(os.path.abspath(i.folder))

    logger.debug('НЕ соответствует число картинок с базой')
    records = Article.select().where(Article.nums_in_folder != Article.nums)
    for i in records:
        if i.art.lower() not in bad_list:
            bad_list_new.append(i.art)
            logger.error(f'Удален {i.art}')
            i.delete_instance()
            shutil.rmtree(i.folder)
        else:
            i.nums = i.nums_in_folder
            i.save()
    return bad_list_new


def clear_bd():
    try:
        with db.atomic():
            db.drop_tables([Article])
    except Exception as ex:
        logger.error(ex)


if __name__ == '__main__':
    start = datetime.now()
    logger.add(
        f"logs/check_bd_{datetime.now().date()}.log",
        rotation="20 MB",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {file!s} | {line} | {message}"
    )
    try:
        count = 0
        ignore_dirs = ['AniKoya', 'DP', 'Bidjo', 'Popsockets', 'ШК', 'Дочке понравилось', 'ПостерДом',
                       'Дочке понравилось']
        sticker_dict = {i.replace('.pdf', '').strip().lower(): os.path.abspath(os.path.join(sticker_path_all, i))
                        for i in os.listdir(sticker_path_all)}

        clear_bd()
        if not Article.table_exists():
            Article.create_table(safe=True)
        for brand, path_brand in brands_paths.items():
            update_arts_db(path_brand, brand)

        bad_list_new = check_bd()
        if bad_list_new:
            logger.debug('Несовпадения в базе')
            logger.info(bad_list_new)
            with open('bad_list.txt', 'w') as f:
                f.write('\n'.join(bad_list_new))
    except Exception as ex:
        logger.error(ex)
        time.sleep(5)
    logger.success(datetime.now() - start)
