import os
import shutil

from loguru import logger
from peewee import fn

from base.db import Article
from blur import blur_image
from config import all_badge, brands_paths


def move_ready_folder(directory: str = f'{all_badge}\\Скаченные с диска',
                      target_directory: str = brands_paths['AniKoya'],
                      shop: str = 'AniKoya'):
    """Перемещение папки и нанесения блюра на края значков, занесение в базу"""
    for folder in os.listdir(directory):
        try:
            folder_path = os.path.abspath(os.path.join(directory, folder))
            target_directory = os.path.abspath(target_directory)

            for i in os.listdir(folder_path):
                new_folder = os.path.join(folder_path, i)
                if os.path.isdir(new_folder):
                    if not os.path.exists(os.path.join(target_directory, i)):
                        shutil.move(new_folder, target_directory)
                        # создание артикула в бд
                        Article.create_with_art(i, os.path.join(target_directory, i), shop=shop)
                        try:
                            art = Article.get_or_none(fn.UPPER(Article.art) == i.upper())
                            if art:
                                folder_name = art.folder
                                for index, filename in enumerate(os.listdir(folder_name), start=1):
                                    if (filename.startswith('!') or filename[0].isdigit()) \
                                            and os.path.isfile(os.path.join(folder_name, filename)):
                                        try:
                                            # Блюр значка
                                            blur_image(image_path=os.path.join(folder_name, filename),
                                                       output_path=os.path.join(folder_name, filename),
                                                       size_b=art.size)
                                        except Exception as ex:
                                            logger.error(ex)
                                            logger.error(os.path.join(folder_name, filename))
                            else:
                                logger.error(f'Не нашелся артикул в бд {i}')
                        except Exception as ex:
                            logger.error(ex)
                    else:
                        logger.error(f'{os.path.join(target_directory, i)} существует')
        except Exception as ex:
            logger.error(ex)
        finally:
            shutil.rmtree(directory)
    return True
