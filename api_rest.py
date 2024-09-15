import json
import os
import shutil
from pprint import pprint

import requests
from loguru import logger

from blur import blur_image
from config import all_badge, sticker_path_all
from db import Article, remove_russian_letters

headers = {'Content-Type': 'application/json'}
# domain = 'http://127.0.0.1:8000/api_rest'
domain = 'https://mycego.online/api_rest'


def get_products(categories: list):
    url = f'{domain}/products/'
    try:
        json_data = json.dumps(categories)
        response = requests.get(url, data=json_data, headers=headers)
        data = response.json().get('data', [])
        return data
    except Exception as ex:
        logger.error(f'Ошибка в запросе по api {ex}')


def get_info_publish_folder(public_url):
    result_data = []
    res = requests.get(
        f'https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_url}&fields=_embedded&limit=1000')
    if res.status_code == 200:
        data = res.json().get('_embedded', {}).get('items', [])
        for i in data:
            file_name = i.get('name', None)
            if file_name:
                file_name = file_name.strip().lower()

            if (os.path.splitext(file_name)[0].isdigit()
                    or 'подл' in file_name
                    or file_name.endswith('.pdf')):
                result_data.append({
                    'name': i.get('name').strip(),
                    'file': i.get('file')
                })

        return result_data


def create_download_data(item):
    url_data = get_info_publish_folder(item['directory_url'])
    if url_data:
        item['url_data'] = url_data
        return item


def get_arts_in_base():
    records = Article.select()
    art_list = list(set(i.art.upper().strip() for i in records))
    return art_list


def download_file(destination_path, url):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(destination_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        file.write(chunk)
            # logger.info(f"File downloaded successfully: {destination_path}")
        else:
            logger.error(f"Error {response.status_code} while downloading file: {url}")
    except requests.RequestException as e:
        logger.error(f"Error during downloading file: {e}")


def blur_images(folder, size):
    for index, filename in enumerate(os.listdir(folder), start=1):
        if (filename.split('.')[0].startswith('!') or filename.split('.')[0].strip().isdigit()) \
                and os.path.isfile(os.path.join(folder, filename)):
            if os.path.exists(os.path.join(folder, filename)):
                try:
                    blur_image(image_path=os.path.join(folder, filename),
                               output_path=os.path.join(folder, filename), size_b=size)
                except Exception as ex:
                    logger.error(ex)
                    logger.error(os.path.join(folder, filename))


def copy_image(image_path, count):
    folder_art = os.path.dirname(image_path)
    exp = image_path.split('.')[-1]
    for i in range(count - 1):
        shutil.copy2(image_path, os.path.join(folder_art, f'{i + 2}.{exp}'))


def main_download_site():
    result_dict_arts = []
    categories = ['Значки']

    art_list = get_arts_in_base()

    data = get_products(categories)

    logger.debug(f'Артикулов в ответе с сервера:{len(data)}')
    data = [item for item in data if remove_russian_letters(item['art'].upper().strip()) not in art_list]
    # data = data[:10]

    # with open('debug\\data_download.json', 'w', encoding='utf-8') as f:
    #     json.dump(data, f, ensure_ascii=False, indent=4)
    # bad_arts = []
    # for item in data:
    #     if 'images' not in item or not item['images']:
    #         bad_arts.append(item)
    #     elif item['the_same'] == 1 and len(item['images']) != 1:
    #         bad_arts.append(item)
    # with open('debug\\badarts.json', 'w', encoding='utf-8') as f:
    #     json.dump(bad_arts, f, ensure_ascii=False, indent=4)

    logger.success(f'Артикулов для загрузки:{len(data)}')
    for item in data:
        download_data = create_download_data(item)
        if download_data:
            result_dict_arts.append(download_data)

    count_task = len(result_dict_arts)
    # with open('data.json', 'w', encoding='utf-8') as f:
    #     json.dump(result_dict_arts, f, ensure_ascii=False, indent=4)

    for index, item in enumerate(result_dict_arts, start=1):
        art = item['art']
        try:
            if art not in art_list:
                brand = item['brand']
                category = item['category']
                size = item['size']
                count = item['quantity']
                folder = os.path.join(all_badge, brand, art)
                if category == 'Значки' and art.split('-')[-1].isdigit() and int(art.split('-')[-2]) != count:
                    logger.error(f'Не совпадает кол-во {art}')
                    continue
                try:
                    os.makedirs(folder, exist_ok=True)
                    for i in item['url_data']:
                        destination_path = os.path.join(folder, i['name'])
                        download_file(destination_path, i['file'])

                    try:
                        size = int(size)
                        blur_images(folder, size)
                    except Exception as ex:
                        logger.error(ex)

                    if item['the_same']:
                        try:
                            if os.path.exists(os.path.join(folder, '1.png')):
                                copy_image(os.path.join(folder, '1.png'), count)
                            elif os.path.exists(os.path.join(folder, '1.jpg')):
                                copy_image(os.path.join(folder, '1.jpg'), count)
                            else:
                                logger.error(f'Нет файла для копирования артикул: {item}')
                                continue
                        except Exception as ex:
                            logger.error(ex)

                    try:
                        for file in os.listdir(folder):
                            if file.endswith('.pdf'):
                                try:
                                    shutil.copy2(os.path.join(folder, file), sticker_path_all)
                                except Exception as ex:
                                    logger.error(ex)
                                else:
                                    os.remove(os.path.join(folder, file))
                        logger.success(f'{index}/{count_task} - {item["art"]}')
                    except Exception as ex:
                        logger.error(ex)

                    Article.create_with_art(art, folder, brand)

                except Exception as ex:
                    logger.error(ex)
            else:
                logger.warning(f'Артикул существует {item["art"]}')
        except Exception as ex:
            logger.error(ex)


if __name__ == '__main__':
    data = get_products(categories=['Значки'])
    with open('debug\\data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
