import os
import shutil

import requests
import tqdm
from loguru import logger

from config import sticker_path_all, all_badge, brands_paths, bad_list
from db import Article, remove_russian_letters, contains_invalid_characters


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


def update_arts_db():
    count = 0
    if not Article.table_exists():
        Article.create_table(safe=True)
    for brand, brand_dir in brands_paths.items():
        for root, dirs, files in os.walk(rf'{brand_dir}'):
            for dir in dirs:
                if len(dir) > 10:
                    count += 1
                    Article.create_with_art(dir, os.path.join(root, dir), brand)
                    print('\r', count, end='', flush=True)

    for root, dirs, files in os.walk(rf'{all_badge}\\Popsockets'):
        for dir in dirs:
            if len(dir) > 10:
                count += 1
                Article.create_with_art(dir, os.path.join(root, dir), 'Popsocket')
                print('\r', count, end='', flush=True)

    print('\nНет подложек')
    records = Article.select().where(Article.skin >> None or Article.images >> None)
    for i in records:
        print(os.path.abspath(i.folder))
        i.delete_instance()
        shutil.rmtree(i.folder)

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
            row.save()


if __name__ == '__main__':
    directory = r'E:\База значков\AniKoya'
    pass
