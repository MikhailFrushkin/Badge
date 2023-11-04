import os
import re
import shutil
import subprocess
import time
from loguru import logger
from blur import blur_size
from utils import delete_files_with_name


def main():
    """Создание файлов по названиям pdf и удаление лишних"""
    directory = r'E:\База значков\сделать'
    directory_sh = r'E:\База значков\сделать\шк'

    for item in os.listdir(directory):

        if os.path.isfile(os.path.join(directory, item)):

            if ('silco' in item.lower() or 'mix' in item.lower() or 'упаковка' in item.lower()
                    or 'фото' in item.lower() or 'mocup' in item.lower() or 'mockup' in item.lower()
                    or 'мокап' in item.lower() or 'размер' in item.lower()
                    or 'джинс' in item.lower() or 'пакет' in item.lower()
                    or 'mix' in item.lower() or 'box' in item.lower()
                    or 'коробка' in item.lower()):
                os.remove(os.path.join(directory, item))

        if (os.path.isfile(os.path.join(directory, item))) and item.endswith('.pdf'):
            if ' (2)' in item:
                old_name = item
                item = item.replace(' (2)', '')
                os.rename(os.path.join(directory, old_name), os.path.join(directory, item))
            os.makedirs(os.path.join(directory, item.replace('.pdf', '')))
            os.remove(os.path.join(directory, item))


def move_dirs():
    """СПеремещение папок в папки по размерам 25,37,44,56"""
    directory = r'E:\База значков\сделать'
    directory_out = r'E:\База значков\сделать'
    for item in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, item)) and item not in ['25', '37', '44', '56', 'шк']:
            if item.endswith('37'):
                shutil.move(os.path.join(directory, item), os.path.join(directory_out + '\\37', item))
            elif item.endswith('56'):
                shutil.move(os.path.join(directory, item), os.path.join(directory_out + '\\56', item))
            elif item.endswith('25'):
                shutil.move(os.path.join(directory, item), os.path.join(directory_out + '\\25', item))
            elif item.endswith('44'):
                shutil.move(os.path.join(directory, item), os.path.join(directory_out + '\\44', item))


def check_duo_skin():
    """Проверка на 2 подложки и отсутствие"""
    directory = r'E:\База значков\AniKoya'
    totalcount = 0
    for item in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, item)):
            count = 0
            for i in os.listdir(os.path.join(directory, item)):
                if not (i.replace('.png', '').
                        replace('.jpg', '').strip().
                        isdigit()) and not i.startswith('!'):
                    count += 1
                    totalcount += 1
            if count > 1:
                logger.error(item)
                if os.path.exists(os.path.join(directory, item)):
                    try:
                        subprocess.Popen(['explorer', os.path.join(directory, item)], shell=True)
                    except Exception as e:
                        print(f"Не удалось открыть папку: {e}")
                else:
                    print("Указанной папки не существует")
            if count == 0:

                logger.error(item)
                if os.path.exists(os.path.join(directory, item)):
                    try:
                        subprocess.Popen(['explorer', os.path.join(directory, item)], shell=True)
                    except Exception as e:
                        print(f"Не удалось открыть папку: {e}")
                else:
                    print("Указанной папки не существует")
    print(totalcount)


def move_ready():
    """Перемещение заблюреных готовых папок в основную папку"""
    target_directory = r'E:\База значков\AniKoya'
    for i in [37, 56]:
        directory = fr'E:\База значков\сделать\{i}'
        for folder_name in os.listdir(directory):
            folder_path = os.path.join(directory, folder_name)
            folder_path_res = os.path.join(target_directory, folder_name)
            if not os.path.exists(folder_path_res):
                shutil.move(folder_path, target_directory)
                print(f'перемещена {folder_name} в {target_directory}')
            else:
                print(f'Папка {folder_name} уже существует в {target_directory}')

    target_directory = r'E:\База значков\DP'
    for i in [25, 44]:
        directory = fr'E:\База значков\сделать\{i}'
        for folder_name in os.listdir(directory):
            folder_path = os.path.join(directory, folder_name)
            folder_path_res = os.path.join(target_directory, folder_name)
            if not os.path.exists(folder_path_res):
                shutil.move(folder_path, target_directory)
                # print(f'перемещена {folder_name} в {target_directory}')
            else:
                print(f'Папка {folder_name} уже существует в {target_directory}')


def move_all_files():
    """Перемещени е всех вложенных файлов из папок в корневую"""
    directory = r'E:\База значков\сделать\старые'
    for folder in os.listdir(directory):
        for root, _, files in os.walk(os.path.join(directory, folder)):
            for file in files:
                print(root)
                if 'круг' not in root and 'готовые' not in root:
                    shutil.move(os.path.join(root, file), os.path.join(directory, file))


def created_dirs():
    """Создание папок по названиям файлов"""
    directory = r'E:\База значков\сделать\старые'
    for i in os.listdir(directory):
        if '-' in i and os.path.isfile(os.path.join(directory, i)):
            name = i.replace('.png', '').replace('.jpg', '').replace('.xcf', '').replace('.pdf', '')

            os.makedirs(os.path.join(directory, name), exist_ok=True)
            os.rename(os.path.join(directory, i), os.path.join(directory, 'Подложка ' + i))


def move_and_blur():
    move_dirs()

    blur_size(25)
    blur_size(37)
    blur_size(44)
    blur_size(56)

    move_ready()


if __name__ == '__main__':
    #
    # main()
    move_and_blur()

    # move_all_files()
    # created_dirs()

    # delete_files_with_name(starting_directory=r'E:\База значков\AniKoya')
    # check_duo_skin()
