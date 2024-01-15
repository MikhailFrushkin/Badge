import os
import shutil

import requests
from loguru import logger

from blur import main
from config import token
from db import Article


def created_folders():
    directory_out = f'D:\Исправить'
    with open('да.txt', 'r') as f:
        art_list = f.read().split('\n')
        rows = Article.select().where(Article.art << art_list)

        for row in rows:
            folder_name = os.path.basename(row.folder)
            logger.debug(folder_name)
            os.makedirs(f'{directory_out}\\{folder_name}', exist_ok=True)
            del_folder_on_yandex(folder_name)


def del_folder_on_yandex(folder):
    headers = {
        "Authorization": f"OAuth {token}"
    }

    params = {
        "path": f'База значков/AniKoya/{folder}',
    }

    response = requests.delete("https://cloud-api.yandex.net/v1/disk/resources", headers=headers, params=params)
    logger.info(response.status_code)


def copy_folder():
    directory_out = 'D:\\База значков\\1'
    with open('да.txt', 'r') as f:
        art_list = f.read().split('\n')
        rows = Article.select().where(Article.art << art_list)

        for row in rows:
            source_folder = row.folder
            folder_name = os.path.basename(source_folder)
            destination_folder = os.path.join(directory_out, folder_name)

            try:
                shutil.copytree(source_folder, destination_folder)
                print(f"Folder '{source_folder}' copied to '{destination_folder}'")
            except PermissionError as pe:
                print(f"PermissionError: {pe}")
            except Exception as e:
                print(f"Error copying folder '{source_folder}': {e}")


if __name__ == '__main__':
    # created_folders()
    # main(file=r'D:\PyCharm\Badge2\Полезное\да.txt', size_b=37)
    copy_folder()
