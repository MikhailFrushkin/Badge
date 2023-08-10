import datetime
import os
import shutil
import subprocess
from pprint import pprint

import cv2
import numpy as np
import requests
import tqdm
from google.oauth2 import service_account
from googleapiclient.discovery import build
from loguru import logger

from config import anikoya_path, dp_path, id_google_table_anikoya, id_google_table_DP, sticker_path_all
from db import add_record_google_table, GoogleTable, Article, db
from utils import rename_files, move_ready_folder, ProgressBar


def read_table_google(CREDENTIALS_FILE='google_acc.json',
                      spreadsheet_id=id_google_table_anikoya,
                      shop='AniKoya', self=None):
    logger.debug(f'Читаю гугл таблицу {shop}')
    self.second_statusbar.showMessage(f'Читаю гугл таблицу {shop}', 10000)

    try:
        credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE)
        service = build('sheets', 'v4', credentials=credentials)
        # Пример чтения файла
        values = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='2023!B1:M30000',
        ).execute()

    except Exception as ex:
        logger.error(f'Ошибка чтения гуглтаблицы {ex}')
    data = values.get('values', [])
    headers = data[0]
    for row in data:
        missing_columns = len(headers) - len(row)
        if missing_columns > 0:
            row += [''] * missing_columns

    headers = data[0]  # Заголовки столбцов из первого элемента списка значений
    rows = data[1:]
    # Проверка количества столбцов и создание DataFrame
    lines_list = []
    if len(headers) != len(rows[0]):
        pprint(headers)
        print(len(headers), len(rows[0]))

        pprint(rows[0])
        print("Ошибка: количество столбцов не совпадает с количеством значений.")
    else:
        progress = ProgressBar(len(rows), self)
        for i in rows:
            if i[4] != '' and i[11] != '':
                add_record_google_table(name=i[0],
                                        quantity=i[1],
                                        designer=i[2],
                                        date=i[3],
                                        folder_link=i[4],
                                        singles=i[5],
                                        mockups=i[6],
                                        packaging=i[7],
                                        checked_by_katya=i[8],
                                        added=i[9],
                                        performer=i[10],
                                        article=i[11],
                                        shop=shop,
                                        )
            progress.update_progress()


# def download_file(url, local_path):
#     response = requests.get(url)
#     with open(f'{local_path}.zip', 'wb') as file:
#         file.write(response.content)

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
        print(f'{public_url} {ex}')


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
        if shop == "DP":
            comp_path = rf'{dp_path}\Скаченные с диска'
        else:
            comp_path = rf'{anikoya_path}\Скаченные с диска'
        os.makedirs(comp_path, exist_ok=True)

        folder_path = download_folder(public_link, local_path, comp_path, self)
        if folder_path:
            new_folder = process_folder(folder_path, comp_path)
            return new_folder
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
    logger.debug(filename)

    image = cv2.imread(filename)
    print(filename)
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


def download_new_arts(link, arts_list, shop, self=None):
    new_folder: str = main_download(public_link=link, shop=shop, self=self)
    logger.debug(link)
    if new_folder:
        if not os.path.exists(new_folder):
            new_folder += '_'
            logger.error(new_folder)
        if not os.path.exists(new_folder):
            logger.error(new_folder)
        article_list = []
        for i in arts_list.split('/'):
            article_list.append(i.strip())
        article_list = [article for article in article_list if len(article) > 6]

        list_image = []
        list_skin_one = []
        list_skin_names = ['подлож', 'главная', 'nabor']
        list_skin_names_one = ['одиноч', 'one', 'подлож']
        for file in os.listdir(new_folder):
            if os.path.isdir(os.path.join(new_folder, file)):
                return
        for file in os.listdir(new_folder):
            if os.path.isfile(os.path.join(new_folder, file)):
                if file.split('.')[1] == 'png' or file.split('.')[1] == 'jpg':
                    if file.split('.')[0].isdigit():
                        list_image.append(file)
                elif file.split('.')[1] == 'pdf':
                    try:
                        shutil.copy2(os.path.join(new_folder, file), sticker_path_all)
                    except Exception as ex:
                        logger.error(ex)

        for name in list_skin_names_one:
            list_skin_one = []
            for file in os.listdir(new_folder):
                if file.split('.')[1] == 'png' or file.split('.')[1] == 'jpg':
                    if name in file.split('.')[0].lower():
                        if 'подлож' in file.split('.')[0].lower() \
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
            for file in os.listdir(new_folder):
                if file.split('.')[1] == 'png' or file.split('.')[1] == 'jpg':
                    if name in file.split('.')[0].lower():
                        list_skin.append(file)
            if len(list_skin) != 0:
                break
        if len(list_skin_one) == 0:
            list_skin_one = [i for i in list_skin if '1' in i.lower() or 'one' in i.lower() or 'мал' in i.lower()]
        list_skin = [i for i in list_skin if i not in list_skin_one]
        print(article_list)
        print(list_skin_one)
        print(list_skin)
        print(list_image)
        for folder in article_list:
            folder_art = os.path.join(new_folder, folder)
            os.makedirs(folder_art, exist_ok=True)
            size = folder.split('-')[-1]
            nums = int(folder.split('-')[-2])

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
    read_table_google(spreadsheet_id=id_google_table_anikoya, shop='AniKoya', self=self)
    read_table_google(spreadsheet_id=id_google_table_DP, shop='DP', self=self)

    records = GoogleTable.select().where(~GoogleTable.status_download)
    list_arts = []
    for row in records:
        temp_list = [i.strip() for i in row.article.split('/') if len(i) < 50]
        if len(temp_list) < 5:
            list_arts.extend(temp_list)
    return list_arts


def download_new_arts_in_comp(list_arts, self=None):
    arts_dict = {}

    for art in list_arts:
        url = GoogleTable.select().where(GoogleTable.article.contains(art)).first()
        arts_dict[url.folder_link] = (url.article, url.shop)
    if self:
        self.second_statusbar.showMessage(f'Скачивание артикулов', 10000)
        process = ProgressBar(len(arts_dict), self)
    for key, value in arts_dict.items():
        try:
            record = GoogleTable.get(folder_link=key)
            record.status_download = True
            record.save()
            print(value)
            download_new_arts(link=key, arts_list=value[0], shop=value[1], self=self)
            if value[1] == 'DP':
                move_ready_folder(directory=rf'{dp_path}\Скаченные с диска',
                                  target_directory=rf'{dp_path}\Готовые\Новые',
                                  shop='DP')
            else:
                move_ready_folder(directory=rf'{anikoya_path}\Скаченные с диска',
                                  target_directory=rf'{anikoya_path}\Готовые\Новые',
                                  shop='AniKoya')
            if self:
                process.update_progress()

        except Exception as ex:
            logger.error(f'{key}, {value}, {ex}')


def update_arts_db():
    count = 0
    start = datetime.datetime.now()
    try:
        db.connect()
        db.drop_tables([Article])
        db.close()
    except Exception as ex:
        logger.error(ex)

    if not Article.table_exists():
        Article.create_table(safe=True)
    for root, dirs, files in os.walk(rf'{dp_path}\Готовые'):
        for dir in dirs:
            if len(dir) > 6:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'DP')
                print('\r', count, end='', flush=True)
    for root, dirs, files in os.walk(rf'{anikoya_path}\Готовые'):
        for dir in dirs:
            if len(dir) > 6:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'AniKoya')
                print('\r', count, end='', flush=True)

    print('Нет подложек')
    records = Article.select().where(Article.skin >> None)
    for i in records:
        print(os.path.abspath(i.folder))

    print('Нет картинок с цифрами')
    records = Article.select().where(Article.images >> None)
    for i in records:
        print(os.path.abspath(i.folder))

    print('НЕ соответствует число картинок с базой')
    records = Article.select().where(Article.nums_in_folder != Article.nums)
    for i in records:
        print(os.path.abspath(i.folder))
        i.nums = i.nums_in_folder
        i.save()
        # subprocess.Popen(f'explorer {os.path.abspath(i.folder)}', shell=True)
        # time.sleep(3)
    logger.debug(datetime.datetime.now() - start)


def update_arts_db2():
    print('Проверка базы: \n')
    count = 0
    start = datetime.datetime.now()

    if not Article.table_exists():
        Article.create_table(safe=True)
    for root, dirs, files in os.walk(rf'{dp_path}\Готовые'):
        for dir in dirs:
            if len(dir) > 6:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'DP')
                print('\r', count, end='', flush=True)
    for root, dirs, files in os.walk(rf'{anikoya_path}\Готовые'):
        for dir in dirs:
            if len(dir) > 6:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'AniKoya')
                print('\r', count, end='', flush=True)

    print('\nНет подложек')
    records = Article.select().where(Article.skin >> None)
    for i in records:
        print(os.path.abspath(i.folder))
        i.delete_instance()

    print('Нет картинок с цифрами')
    records = Article.select().where(Article.images >> None)
    for i in records:
        print(os.path.abspath(i.folder))
        i.delete_instance()

    print('НЕ соответствует число картинок с базой')
    records = Article.select().where(Article.nums_in_folder != Article.nums)
    for i in records:
        print(os.path.abspath(i.folder))
        i.nums = i.nums_in_folder
        i.save()
        # subprocess.Popen(f'explorer {os.path.abspath(i.folder)}', shell=True)
        # time.sleep(3)
    logger.debug(datetime.datetime.now() - start)


def update_sticker_path():
    no_stickers_rows = Article.select().where(Article.sticker >> None)
    files_list = os.listdir(sticker_path_all)
    for row in no_stickers_rows:
        name_sticker = row.art + '.pdf'
        for file_name in files_list:
            if file_name == name_sticker or file_name.lower() == name_sticker:
                row.sticker = os.path.join(sticker_path_all, file_name)
                print('найден ШК: ', os.path.join(sticker_path_all, file_name))
                row.save()
                break


if __name__ == '__main__':
    update_arts_db()
    # update_arts_db2()
    # update_sticker_path()
