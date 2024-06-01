import asyncio
import datetime
import os
import re
import shutil
import subprocess
from pprint import pprint

import cv2
import numpy as np
import pandas as pd
import requests
import tqdm
from PyQt5.QtWidgets import QMessageBox
from google.oauth2 import service_account
from googleapiclient.discovery import build
from loguru import logger

from blur import blur_size
from config import anikoya_path, dp_path, sticker_path_all, all_badge
from db import add_record_google_table, GoogleTable, Article, db, remove_russian_letters, contains_invalid_characters
from utils import rename_files, move_ready_folder, ProgressBar


# def read_table_google(CREDENTIALS_FILE='Настройки\\google_acc.json',
#                       spreadsheet_id=id_google_table_anikoya,
#                       shop='AniKoya', self=None, sheet_name='2023'):
#     logger.debug(f'Читаю гугл таблицу {shop}')
#     if self:
#         self.second_statusbar.showMessage(f'Читаю гугл таблицу {shop}', 10000)
#
#     try:
#         credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
#         service = build('sheets', 'v4', credentials=credentials)
#         values = service.spreadsheets().values().get(
#             spreadsheetId=spreadsheet_id,
#             range=sheet_name,
#         ).execute()
#     except Exception as ex:
#         logger.error(f'Ошибка чтения гуглтаблицы {ex}')
#         try:
#             credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
#             service = build('sheets', 'v4', credentials=credentials)
#             values = service.spreadsheets().values().get(
#                 spreadsheetId=spreadsheet_id,
#                 range='2024',
#             ).execute()
#         except Exception as ex:
#             logger.error(f'Ошибка чтения гуглтаблицы {ex}')
#
#     data = values.get('values', [])
#     rows = data[1:]
#     headers = [i for i in data[0]]
#     headers.append(' ')
#     for row in data:
#         missing_columns = len(headers) - len(row)
#         if missing_columns > 0:
#             row += [''] * missing_columns
#     df = pd.DataFrame(data[1:], columns=headers)
#     art_name_col = None
#     url_name_col = None
#     name_name_col = None
#     for i in headers:
#         if shop == "AniKoya" or shop == "DP":
#             if 'артикул' in i.lower():
#                 art_name_col = i
#         else:
#             if ('артикул' in i.lower()
#                     and 'вб' not in i.lower() and 'озон' not in i.lower()
#                     and 'wb' not in i.lower() and 'ozon' not in i.lower()):
#                 art_name_col = i
#
#         if ('ссылка' in i.lower()
#                 and 'вб' not in i.lower() and 'озон' not in i.lower()
#                 and 'wb' not in i.lower() and 'ozon' not in i.lower()):
#             url_name_col = i
#         if 'наимен' in i.lower():
#             name_name_col = i
#
#     if len(headers) != len(rows[0]):
#         logger.error("Ошибка: количество столбцов не совпадает с количеством значений.")
#     else:
#         for index, row in df.iterrows():
#             try:
#                 if row[art_name_col] == '' or '-' not in row[art_name_col] or not row[url_name_col].startswith(
#                         'https://disk'):
#                     continue
#                 else:
#                     add_record_google_table(
#                         name=row[name_name_col] if name_name_col else 'Не найден столбец наименование',
#                         folder_link=row[url_name_col],
#                         article=row[art_name_col],
#                         shop=shop,
#                     )
#             except Exception as ex:
#                 logger.error(row)
#                 logger.error(ex)
#                 QMessageBox.warning(self, 'Ошибка', f'Ошибка записи ссылки в базу\n{index}{ex}')


def download_file(url, local_path):
    with open(f'{local_path}.zip', 'wb') as f:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))

            tqdm_params = {
                # 'desc': url,
                'total': total,
                'miniters': 1,
                'unit': 'it',
                'unit_scale': True,
                'unit_divisor': 1024,
            }

            with tqdm.tqdm(**tqdm_params) as pb:
                for chunk in r.iter_content(chunk_size=8192):
                    pb.update(len(chunk))
                    f.write(chunk)


def get_yandex_disk_files(public_url):
    try:
        url = f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_url}"
        response = requests.get(url)
        data = response.json()
        if "items" in data['_embedded']:
            return data['name'].strip()
        return None
    except Exception as ex:
        logger.error(f'{public_url} {ex}')


def download_folder(public_link, local_path, comp_path, self=None):
    """Загрузка публичной папки со значками"""
    api_url = 'https://cloud-api.yandex.net/v1/disk/public/resources/download'
    params = {
        'public_key': public_link
    }
    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        download_data = response.json()
        href = download_data['href']
        # Получение имени папки на яндекс диске
        path = get_yandex_disk_files(public_link)
        folder_path = os.path.join(local_path, path)
        if os.path.exists(os.path.join(comp_path, path)):
            return
        if contains_invalid_characters(path):
            logger.error(f'f"Имя файла {path} содержит недопустимые символы."')
            logger.error(href)
            return
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            logger.success(f'Скачивание {os.path.join(folder_path, path.split("/")[-1])}')
            if self:
                self.second_statusbar.showMessage(f'Скачивание {os.path.join(folder_path, path.split("/")[-1])}', 10000)
            download_file(href, os.path.join(folder_path, path.split('/')[-1]))
            if 'items' in download_data:
                for item in download_data['items']:
                    download_folder(item['href'], folder_path)
        else:
            logger.debug(f"Папка уже скачена: {folder_path}")
        return folder_path


def extract_archive(archive_path, destination_path):
    """Распаковка скачаного архива"""
    try:
        name = os.path.splitext(os.path.basename(archive_path))[0]
        folder = os.path.join(destination_path, name)
        if not os.path.exists(folder):
            subprocess.run(['7z', 'x', archive_path, '-o' + destination_path])
            shutil.rmtree(os.path.join('C:\\temp', os.path.dirname(archive_path)))
        return folder
    except Exception as ex:
        logger.error(ex)


def process_folder(folder_path, destination_path):
    new_folder = None
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            if '.zip' not in file_path:
                try:
                    if not os.path.exists(file_path + '.zip'):
                        base_path, _ = os.path.splitext(file_path)
                        new_file_path = base_path + '.zip'
                        os.rename(file_path, new_file_path)
                        file_path = base_path + '.zip'
                    new_folder = extract_archive(file_path, destination_path)
                except Exception as ex:
                    logger.error(ex)
            else:
                try:
                    new_folder = extract_archive(file_path, destination_path)
                except Exception as ex:
                    logger.error(ex)
    return new_folder


def main_download(public_link, shop, self=None):
    try:
        local_path = r'C:\temp'
        os.makedirs(local_path, exist_ok=True)
        comp_path = rf'{all_badge}\Скаченные с диска'
        os.makedirs(comp_path, exist_ok=True)

        folder_path = download_folder(public_link, local_path, comp_path, self)
        if folder_path:
            new_folder = process_folder(folder_path, comp_path)
            return os.path.abspath(new_folder)
        else:
            logger.error('Не скачался архив либо папка уже существует в директории')

    except Exception as ex:
        logger.error(f"не удалось скачать: {public_link} {ex}")


def search_one_image(skin, images_list, output_folder):
    source_image = cv2.imread(skin)
    images_stat = tuple()
    # Загрузите алгоритм выделения особенностей и создайте детектор
    orb = cv2.ORB_create()

    # Найдите особенности и дескрипторы для исходного искомого изображения
    kp1, des1 = orb.detectAndCompute(source_image, None)

    # Пройдите по каждому изображению и найдите совпадения
    for target_image_path in images_list:
        count = 0
        # Загрузите текущее изображение
        target_image = cv2.imread(target_image_path)

        # Найдите особенности и дескрипторы для текущего изображения
        kp2, des2 = orb.detectAndCompute(target_image, None)

        # Найдите совпадения между дескрипторами
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        # Отсортируйте совпадения по расстоянию
        matches = sorted(matches, key=lambda x: x.distance)

        # Выведите первые несколько совпадений
        for match in matches[:15]:
            count += match.distance
        images_stat += ((target_image_path, count),)
    sorted_data = sorted(images_stat, key=lambda x: x[1])
    # logger.success(f"Найденна единичка в {sorted_data[0]} для {skin}")
    shutil.copy2(sorted_data[0][0], output_folder)
    return sorted_data[0][0]


def search_image_56(folder_skin, output_folder):
    """Вырезание круга с подложки"""
    filename = os.path.abspath(folder_skin)
    image = cv2.imread(filename)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    # Детекция кругов на изображении
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, minDist=600,
                               param1=133, param2=35, minRadius=500, maxRadius=600)
    if circles is not None:
        # Округление координат и радиусов кругов
        circles = np.round(circles[0, :]).astype(int)
        # Создание папки для сохранения найденных кругов
        for i, (x, y, r) in enumerate(circles, start=1):
            # Создаем новое изображение с белым фоном
            output_img = np.ones_like(image) * 255
            # Создаем маску круга
            mask = np.zeros_like(gray)
            cv2.circle(mask, (x, y), r, (255), -1)
            # Применяем маску к исходному изображению
            output_img = np.where(mask[..., None] == 255, image, output_img)
            # Обрезаем изображение до краев
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            x_min, y_min, w, h = cv2.boundingRect(contours[0])
            output_img = output_img[y_min:y_min + h, x_min:x_min + w]
            # Сохраняем изображение с белым фоном
            cv2.imwrite(os.path.join(output_folder, f'Картинка{i}.png'), output_img)
            return os.path.join(output_folder, f'Картинка{i}.png')
    else:
        logger.error("Круги не найдены на изображении.")
        with open('bad.txt', 'a') as f:
            f.write(f"{output_folder}\n")


def download_new_arts(link, list_arts, shop, self=None):
    main_download(public_link=link, shop=shop, self=self)
    logger.debug(link)
    new_folder = os.path.join(f'{all_badge}\\Скаченные с диска', os.listdir(f'{all_badge}\\Скаченные с диска')[0])
    logger.debug(new_folder)
    files_in_dir = os.listdir(new_folder)
    if new_folder:
        arts_list = []
        list_image = []
        list_skin_one = []
        list_skin_names = ['под', 'главная', 'nabor']
        list_skin_names_one = ['одиноч', 'one', 'под']
        for file in files_in_dir:
            if os.path.isdir(os.path.join(new_folder, file)):
                return
        for file in files_in_dir:
            if os.path.isfile(os.path.join(new_folder, file)):
                if file.replace('.png', '').replace('.jpg', '').strip().isdigit():
                    list_image.append(file)
                elif file.endswith('.pdf') and '-' in file:
                    try:
                        arts_list.append(file.replace('.pdf', ''))
                        logger.success(f'Найден стикер {file}\nСкопирован в папку {sticker_path_all}')
                        shutil.copy2(os.path.join(new_folder, file), sticker_path_all)
                    except Exception as ex:
                        logger.error(ex)
        if not arts_list:
            arts_list = list_arts.replace('\r', ' ').replace('\n', ' ')
            delimiters = r'[\\/|, ]'
            substrings = re.split(delimiters, arts_list)
            arts_list = [substring.strip() for substring in substrings if substring.strip()]
            logger.debug(arts_list)
        for name in list_skin_names_one:
            list_skin_one = []
            for file in files_in_dir:
                if file.split('.')[1] == 'png' or file.split('.')[1] == 'jpg':
                    if name in file.split('.')[0].lower():
                        if 'под' in file.split('.')[0].lower() \
                                and '1' not in file.split('.')[0].lower() \
                                and '11' not in file.split('.')[0].lower() \
                                and '12' not in file.split('.')[0].lower() \
                                and '15' not in file.split('.')[0].lower() \
                                and '111' not in file.split('.')[0].lower() \
                                :
                            continue
                        list_skin_one.append(file)
            if len(list_skin_one) != 0:
                break

        for name in list_skin_names:
            list_skin = []
            for file in files_in_dir:
                if file.split('.')[1] == 'png' or file.split('.')[1] == 'jpg':
                    if name in file.split('.')[0].lower():
                        list_skin.append(file)
            if len(list_skin) != 0:
                break
        if len(list_skin_one) == 0:
            list_skin_one = [i for i in list_skin if '1' in i.lower() or 'one' in i.lower() or 'мал' in i.lower()]
            if len(list_skin_one) == 0:
                list_skin_one = list_skin[:]
        list_skin = [i for i in list_skin if i not in list_skin_one]
        print("Артикула: ", arts_list)
        print("Наклейки одиночки: ", list_skin_one)
        print("Наклейки наборы: ", list_skin)
        print("Изображения значков: ", list_image)

        for folder in arts_list:
            folder_art = os.path.join(new_folder, folder)
            os.makedirs(folder_art, exist_ok=True)
            size = folder.split('-')[-1]
            nums = int(folder.split('-')[-2])
            logger.success(size)
            logger.success(nums)
            if len(list_image) == 1:
                if nums == 1:
                    shutil.copy2(os.path.join(new_folder, list_image[0]), folder_art)
                    temp_list_skin_one_temp = []
                    temp_list_skin_one_temp.extend(list_skin_one)
                    temp_list_skin_one_temp.extend(list_skin)
                    if len(temp_list_skin_one_temp) == 1:
                        shutil.copy2(os.path.join(new_folder, temp_list_skin_one_temp[0]), folder_art)
                        rename_files(os.path.join(folder_art, temp_list_skin_one_temp[0]), 'Подложка')
                    for j in list_skin_one:
                        if size in j:
                            try:
                                shutil.copy2(os.path.join(new_folder, j), folder_art)
                                rename_files(os.path.join(folder_art, j), 'Подложка')
                                break
                            except Exception as ex:
                                logger.error(ex)
                else:
                    for q in range(nums):
                        try:
                            shutil.copy2(os.path.join(new_folder, list_image[0]),
                                         os.path.join(folder_art, f'{q}' + list_image[0]))
                        except IOError as e:
                            logger.error(f"Error copying the file: {e}")
                    for j in list_skin:
                        if size in j:
                            try:
                                shutil.copy2(os.path.join(new_folder, j), folder_art)
                                rename_files(os.path.join(folder_art, j), 'Подложка')
                                break
                            except Exception as ex:
                                logger.error(ex)
            else:
                if nums == 1:
                    for j in list_skin_one:
                        if len(list_skin_one) == 1:
                            try:
                                shutil.copy2(os.path.join(new_folder, j), folder_art)
                                new_path_skin = rename_files(os.path.join(folder_art, j), 'Подложка')
                            except Exception as ex:
                                logger.error(ex)
                            try:
                                skin = search_image_56(folder_skin=new_path_skin,
                                                       output_folder=folder_art)
                            except Exception as ex:
                                logger.error(ex)
                            try:
                                if skin:
                                    images_list = [os.path.join(new_folder, path) for path in list_image]
                                    search_one_image(skin, images_list, folder_art)
                                    break
                            except Exception as ex:
                                logger.error(ex)
                        else:
                            if size in j:
                                try:
                                    shutil.copy2(os.path.join(new_folder, j), folder_art)
                                    new_path_skin = rename_files(os.path.join(folder_art, j), 'Подложка')
                                except Exception as ex:
                                    logger.error(ex)
                                skin = search_image_56(folder_skin=new_path_skin,
                                                       output_folder=folder_art)
                                if skin:
                                    images_list = [os.path.join(new_folder, path) for path in list_image]
                                    search_one_image(skin, images_list, folder_art)
                                    break
                else:
                    for i in list_image:
                        shutil.copy2(os.path.join(new_folder, i), folder_art)
                    for j in list_skin:
                        if len(list_skin) == 1:
                            shutil.copy2(os.path.join(new_folder, j), folder_art)
                            rename_files(os.path.join(folder_art, j), 'Подложка')
                            break
                        else:
                            if size in j:
                                shutil.copy2(os.path.join(new_folder, j), folder_art)
                                rename_files(os.path.join(folder_art, j), 'Подложка')
                                break


def update_db(self=None):
    # Чтение гугл таблицы
    # try:
    #     read_table_google(spreadsheet_id=id_google_table_anikoya, shop='AniKoya', self=self)
    #     read_table_google(spreadsheet_id=id_google_table_DP, shop='DP', self=self)
    #     read_table_google(shop='Popsocket', sheet_name='ПОПСОКЕТЫ 2023')
    # except Exception as ex:
    #     logger.error(ex)
    #     QMessageBox.warning(self, 'Ошибка', f'Ошибка сканирования гугл таблицы\n {ex}')
    records = GoogleTable.select().where(~GoogleTable.status_download)
    list_arts = []
    list_arts_popsocket = []
    try:
        for row in records:
            if row.shop == 'AniKoya' or row.shop == 'DP':
                delimiters = r'[\\/|, ]'
                substrings = re.split(delimiters, row.article)
                temp_list = [substring.strip() for substring in substrings if substring.strip()]
                if 0 > len(temp_list) > 4:
                    logger.debug(f'{row.id}: {temp_list}')
                else:
                    list_arts.extend(temp_list)
            if row.shop == 'Popsocket':
                list_arts_popsocket.append(row)
    except Exception as ex:
        logger.error(ex)
    return list_arts, list_arts_popsocket


def download_new_arts_in_comp(list_arts, self=None):
    arts_dict = {}

    for art in list_arts:
        url = (GoogleTable.select().where(GoogleTable.article.contains(art) & ~GoogleTable.status_download)
               .order_by(GoogleTable.created_at.desc()).first())
        arts_dict[url.folder_link] = (url.article, url.shop)
    if self:
        self.second_statusbar.showMessage(f'Скачивание артикулов', 10000)
        process = ProgressBar(len(arts_dict), self)
    for key, value in arts_dict.items():
        record = GoogleTable.get(folder_link=key)
        record.status_download = True
        record.save()
        try:
            download_new_arts(link=key, list_arts=value[0], shop=value[1], self=self)
            if value[1] == 'DP':
                move_ready_folder(target_directory=f'{dp_path}',
                                  shop='DP')
            else:
                move_ready_folder()
            if self:
                process.update_progress()
        except Exception as ex:
            logger.error(f'{key}, {value}, {ex}')


def update_arts_db2():
    ignore_dirs = ['AniKoya', 'DP', 'Popsockets', 'Значки ШК', 'сделать']
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

    count = 0

    if not Article.table_exists():
        Article.create_table(safe=True)
    for root, dirs, files in os.walk(rf'{dp_path}'):
        for dir in dirs:
            if len(dir) > 10:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'DP')
                print('\r', count, end='', flush=True)
    for root, dirs, files in os.walk(rf'{anikoya_path}'):
        for dir in dirs:
            if len(dir) > 10:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'AniKoya')
                print('\r', count, end='', flush=True)

    for root, dirs, files in os.walk(rf'{all_badge}\\Popsockets'):
        for dir in dirs:
            if len(dir) > 10:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'Popsocket')
                print('\r', count, end='', flush=True)

    print('\nНет подложек')
    records = Article.select().where(Article.skin >> None)
    for i in records:
        print(os.path.abspath(i.folder))
        i.delete_instance()
        shutil.rmtree(i.folder)
        # shutil.move(i.folder, r'E:\Новая база значков\Проблемные')

    print('Нет картинок с цифрами')
    records = Article.select().where(Article.images >> None)
    for i in records:
        print(os.path.abspath(i.folder))
        i.delete_instance()
        shutil.rmtree(i.folder)
        # shutil.move(i.folder, r'E:\Новая база значков\Проблемные')

    print('НЕ соответствует число картинок с базой')
    records = Article.select().where(Article.nums_in_folder != Article.nums)
    for i in records:
        print(os.path.abspath(i.folder))
        if i.art.lower() not in bad_list:
            logger.error(f'Удален {i.art}')
            i.delete_instance()
            shutil.rmtree(i.folder)
        else:
            i.nums = i.nums_in_folder
            i.save()
        # subprocess.Popen(f'explorer {os.path.abspath(i.folder)}', shell=True)
        # time.sleep(3)


def update_sticker_path():
    no_stickers_rows = Article.select().where(Article.sticker >> None)
    all_stickers = os.listdir(sticker_path_all)
    all_stickers_rev_rush = list(map(remove_russian_letters, list(map(str.lower, all_stickers))))
    for index, row in enumerate(no_stickers_rows, start=1):
        name_sticker = row.art + '.pdf'
        if name_sticker in all_stickers_rev_rush:
            sticker_file_path = os.path.join(sticker_path_all, all_stickers[all_stickers_rev_rush.index(name_sticker)])
            row.sticker = os.path.join(sticker_path_all, sticker_file_path)
            # print(f'{index} найден ШК: {row.art} ', os.path.join(sticker_path_all, sticker_file_path))
            row.save()



if __name__ == '__main__':
    # read_table_google()
    # read_table_google(spreadsheet_id=id_google_table_DP, shop='DP')
    directory = r'E:\База значков\AniKoya'
    count = 1
    for index, item in enumerate(os.listdir(directory), start=1):
        try:
            num = int(item.split("-")[-2])
            records_num = Article.get(Article.art == item).nums_in_folder
            if num != records_num and num > 10:
                print(f'{count} {item}  {num}/{records_num}')
                print(os.path.join(directory, item))
                count += 1
        except Exception as ex:
            pass
            # logger.error(f'{item} {ex} ')
