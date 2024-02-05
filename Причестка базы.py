import os
import re
import shutil
import subprocess
from datetime import datetime

from loguru import logger
from peewee import *

from config import sticker_path_all, dp_path, anikoya_path, all_badge
from db import Article

db = SqliteDatabase('mydatabase.db')


def main():
    # records = Article.select().where((Article.shop == 'AniKoya')
    records = Article.select().where((Article.shop == 'AniKoya') & (Article.sticker.is_null(False)))
    logger.debug(len(records))
    for i in records:
        # try:
        #     files = [i for i in os.listdir(i.folder)
        #              if not i.split('.')[0].isdigit()
        #              # and not i.startswith('!')
        #              and ('Подложка' not in i)
        #              ]
        #     if files:
        #         print(os.path.abspath(i.folder))
        #         for index, file in enumerate(files, start=1):
        #             exp = file.split('.')[-1]
        #             # new_name = os.path.join(i.folder, f'{index}.{exp}')
        #             new_name = os.path.join(i.folder, f'Подложка.png')
        #             try:
        #                 os.rename(os.path.join(i.folder, file), new_name)
        #             except Exception as e:
        #                 print(f"Не переименовать: {i}")
        #
        #         if os.path.exists(os.path.abspath(i.folder)):
        #             try:
        #                 subprocess.Popen(['explorer', os.path.abspath(i.folder)], shell=True)
        #             except Exception as e:
        #                 print(f"Не удалось открыть папку: {e}")
        # except Exception as e:
        #     print(f"Не удалось открыть папку: {e}")

        try:
            if os.path.exists(i.sticker):
                logger.success(f"Скопирован стикер: {os.path.abspath(i.folder)}")
                shutil.copy2(i.sticker, i.folder)
            else:
                logger.error(os.path.abspath(i.folder))
        except Exception as e:
            print(f"Не удалось открыть папку: {e}")


if __name__ == '__main__':
    main()