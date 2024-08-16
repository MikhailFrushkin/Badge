import os
import re
import shutil
from datetime import datetime

from loguru import logger
from peewee import *

from config import sticker_path_all, dp_path, anikoya_path, all_badge, Bidjo_path

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
            if '11new' in art or '12new' in art or '13new' in art or '14new' in art or '15new' in art:
                logger.error(art)
                logger.error(os.path.abspath(folder))
                # shutil.rmtree(os.path.abspath(folder))
                return
            nums = None
            if art.endswith('56'):
                size = 56
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
    if not Article.table_exists():
        Article.create_table(safe=True)
    global count
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for dir in dirs:
                if dir not in ignore_dirs:
                    count += 1
                    Article.create_with_art(dir, os.path.join(root, dir), shop)
                    print('\r', count, end='', flush=True)


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
        # logger.info(os.path.abspath(i.folder))
        # if os.path.exists(os.path.abspath(i.folder)):
        #     try:
        #         subprocess.Popen(['explorer', os.path.abspath(i.folder)], shell=True)
        #     except Exception as e:
        #         print(f"Не удалось открыть папку: {e}")
        # else:
        #     print("Указанной папки не существует")

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
        ignore_dirs = ['AniKoya', 'DP', 'Bidjo', 'Popsockets', 'Значки ШК', 'сделать']
        bad_list = ['amazingmauricenabor-12new-6-44', 'che_guevara-44-6', 'harrypotternabor-12new-6-44',
                    'rodi_deadplate-13new-2-44', 'sk-13new-1-44', 'spongebob-13new-6-44', 'tatianakosach-13new-44-1',
                    'tatianakosach-13new-44-6', 'toya_kaito-13new-2-44', 'velvet_venir-13new-2-44', 'yanderirui-13new-44-1',
                    'yanderirui-13new-44-6', 'zavdv-nabor-13new-6-44', 'zvezdnoenebo-13new-44-1', 'aespanabor-7new-8-37',
                    'allforthegamenabor-7new-10-37', 'allforthegamenabor-7new-10-56', 'allforthegamenabor-7new-6-37',
                    'allforthegamenabor-7new-6-56', 'bsd.dadzai_azushi-13new-6-37', 'bsd.dadzai_azushi-13new-6-56',
                    'coldheartnabor-7new-10-37', 'coldheartnabor-7new-10-56', 'coldheartnabor-7new-6-37',
                    'coldheartnabor-7new-6-56', 'doki_ny-13new-6-37', 'doki_ny-13new-6-56', 'glaza2-13new-1-37',
                    'glaza2-13new-1-56', 'hask2-13new-2-56', 'initiald-13new-4-37', 'initiald-13new-4-56',
                    'jojonabor-7new-10-37', 'jojonabor-7new-10-56', 'jojonabor-7new-6-37', 'jojonabor-7new-6-56',
                    'justinbieber-11new-6-37', 'justinbieber-11new-6-56', 'kamilla_valieva-13new-6-37',
                    'kamilla_valieva-13new-6-56', 'kang_yuna-13new-6-37', 'kang_yuna-13new-6-56',
                    'kimkardashian-11new-6-37', 'kimkardashian-11new-6-56', 'kittyisnotacat-13new-6-37',
                    'kittyisnotacat-13new-6-56', 'maiorgromnabor-7new-10-37', 'maiorgromnabor-7new-10-56',
                    'maiorgromnabor-7new-6-37', 'maiorgromnabor-7new-6-56', 'minecraft-nabor-7new-10-37',
                    'minecraft-nabor-7new-10-56', 'minecraft-nabor-7new-6-37', 'minecraft-nabor-7new-6-56',
                    'newjeans8-13new-6-37', 'newjeans8-13new-6-56', 'nydragon_simvol-13new-6-37',
                    'nydragon_simvol-13new-6-56', 'omori_hero-13new-6-37', 'omori_hero-13new-6-56',
                    'papini.dochki-13new-6-37', 'papini.dochki-13new-6-56', 'pokrov3-13new-6-37', 'pokrov3-13new-6-56',
                    'pomni-13new-8-37', 'pomni-13new-8-56', 'pyro_genshini-13new-6-37', 'pyro_genshini-13new-6-56',
                    'rojdestwo-13new-6-37', 'rojdestwo-13new-6-56', 'sekaiproject-11new-6-37', 'sekaiproject-11new-6-56',
                    'seohaebom-13new-6-37', 'seohaebom-13new-6-56', 'sindromvosmiklassnika-6-37',
                    'sindromvosmiklassnika-6-56', 'socialpath_sk-13new-6-56', 'spidermannabor-7new-10-37',
                    'spidermannabor-7new-10-56', 'taylorswift-11new-6-37', 'taylorswift-11new-6-56',
                    'tomorrowxtogether-8new-10-37', 'tomorrowxtogether-8new-10-56', 'tomorrowxtogether-8new-6-37',
                    'tomorrowxtogether-8new-6-56', 'vipysknik_starsheigroup-11new-6-37',
                    'vipysknik_starsheigroup-11new-6-56', 'vinil.skrech-13new-6-37', 'vinil.skrech-13new-6-56']

        sticker_dict = {i.replace('.pdf', '').strip().lower(): os.path.abspath(os.path.join(sticker_path_all, i))
                        for i in os.listdir(sticker_path_all)}

        clear_bd()

        update_arts_db(dp_path, 'DP')
        update_arts_db(anikoya_path, 'AniKoya')
        update_arts_db(Bidjo_path, 'Bidjo')
        update_arts_db(rf'{all_badge}\\Popsockets', 'Popsocket')

        bad_list_new = check_bd()
        if bad_list_new:
            logger.debug('Несовпадения в базе')
            logger.info(bad_list_new)
            with open('bad_list.txt', 'w') as f:
                f.write('\n'.join(bad_list_new))
    except Exception as ex:
        logger.error(ex)
    logger.success(datetime.now() - start)
