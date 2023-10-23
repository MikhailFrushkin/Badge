import os
import re
import shutil
import subprocess
import time

from loguru import logger

from utils import delete_files_with_name


def main():
    directory = r'E:\База значков\сделать'
    directory_sh = r'E:\База значков\сделать\шк'

    for item in os.listdir(directory):

        if os.path.isfile(os.path.join(directory, item)):

            if ('silco' in item.lower() or 'mix' in item.lower() or 'упаковка' in item.lower()
                    or 'фото' in item.lower() or 'nabor' in item.lower()
                    or 'мокап' in item.lower() or 'размер' in item.lower()):
                os.remove(os.path.join(directory, item))

        if (os.path.isfile(os.path.join(directory, item))) and item.endswith('.pdf'):
            os.makedirs(os.path.join(directory, item.replace('.pdf', '')))
            shutil.move(os.path.join(directory, item), os.path.join(directory_sh, item))


def move_dirs():
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
    directory = r'E:\База значков\AniKoya'
    totalcount = 0
    for item in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, item)):
            count = 0
            for i in os.listdir(os.path.join(directory, item)):
                if not (i.replace('.png', '').
                        replace('.jpg', '').
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


if __name__ == '__main__':
    # main()
    # move_dirs()
    # delete_files_with_name(starting_directory=r'E:\База значков\AniKoya')
    check_duo_skin()
