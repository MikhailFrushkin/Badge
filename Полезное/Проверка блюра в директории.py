import os
import shutil

import requests
from loguru import logger

from config import token


def main():
    for item in os.listdir(directory):
        # Папка которую нужно скопировать
        copy_folder = rf'D:\База значков\DP\{item}'
        # Путь к новой папки
        new_folder = os.path.join(directory2, item)
        try:
            # shutil.copytree(copy_folder, new_folder)
            del_folder_y(item)
            print(f"Папка успешно скопирована: {copy_folder}")
        except PermissionError as e:
            print(f"Ошибка при копировании папки {copy_folder}: {e}")
        except Exception as e:
            print(f"Произошла ошибка: {e}")


def del_folder_y(folder):
    """Удаление папки на Яндекс.Диске.
    path: Путь к удаляемой папке."""
    path = f'База значков/DP/{folder}'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {token}'}
    res = requests.delete(f'https://cloud-api.yandex.net/v1/disk/resources?path={path}',
                          headers=headers)
    if res.status_code in [202, 204]:
        logger.info(f"Folder '{path}' deleted successfully.")
    else:
        logger.error(f"Error {res.status_code}: {res.text}")


if __name__ == '__main__':
    directory = r'D:\База значков\fix'
    directory2 = r'D:\База значков\Заменить на я'
    main()
