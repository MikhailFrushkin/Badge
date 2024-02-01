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
    records = Article.select()
    for i in records:
        files = [i for i in os.listdir(i.folder)
                 if not i.split('.')[0].isdigit()
                 # and not i.startswith('!')
                 and i != 'Подложка.png'
                 ]
        if files:
            print(os.path.abspath(i.folder))
            print(files)
            # for index, file in enumerate(files, start=1):
            #     exp = file.split('.')[-1]
            #     new_name = os.path.join(i.folder, f'{index}.{exp}')
            #     print(new_name)
            #     try:
            #         os.rename(os.path.join(i.folder, file), new_name)
            #     except Exception as e:
            #         print(f"Не переименовать: {i}")

            # if os.path.exists(os.path.abspath(i.folder)):
            #     try:
            #         subprocess.Popen(['explorer', os.path.abspath(i.folder)], shell=True)
            #     except Exception as e:
            #         print(f"Не удалось открыть папку: {e}")

if __name__ == '__main__':
    main()