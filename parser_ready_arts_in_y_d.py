import asyncio
import os
import time
from pprint import pprint
from urllib.parse import quote

import aiofiles
import aiohttp
from loguru import logger

from config import token, all_badge

semaphore = asyncio.Semaphore(2)


async def traverse_yandex_disk(session, folder_path, result_dict, offset=0):
    limit = 1000  # Максимальное количество элементов, которые можно получить за один запрос
    url = f"https://cloud-api.yandex.net/v1/disk/resources?path={quote(folder_path)}&limit={limit}&offset={offset}"
    headers = {"Authorization": f"OAuth {token}"}

    try:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            tasks = []

            for item in data["_embedded"]["items"]:
                if item["type"] == "dir" and (item["name"] not in result_dict):
                    if len(item["name"]) > 8 and item["name"] != 'Значки ШК' and item["name"] != 'Новые значки':
                        print(item["name"])
                        result_dict[item["name"].lower()] = item["path"]
                    task = traverse_yandex_disk(session, item["path"], result_dict)
                    tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks)

            # Проверяем, есть ли ещё элементы для сканирования
            total = data["_embedded"]["total"]
            offset += limit
            if offset < total:
                # Рекурсивно вызываем функцию для следующей порции элементов
                await traverse_yandex_disk(session, folder_path, result_dict, offset)

    except Exception as ex:
        # logger.debug(f'Ошибка при поиске папки {folder_path} {ex}')
        pass


async def main_search():
    folder_path = '/Компьютер HOME-PC/База значков'
    result_dict = {}
    async with aiohttp.ClientSession() as session:
        await traverse_yandex_disk(session, folder_path, result_dict)

    # df = pd.DataFrame(list(result_dict.items()), columns=['Имя', 'Путь'])
    # logger.info('Создан документ Пути к артикулам.xlsx')
    # df_in_xlsx(df, 'Пути к артикулам')

    time.sleep(30)
    return result_dict


async def get_download_link(session, token, file_path):
    headers = {"Authorization": f"OAuth {token}"}
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    params = {"path": file_path}

    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data["href"]
    except asyncio.TimeoutError:
        logger.error(f"Время ожидания ответа от сервера истекло для файла '{file_path}'.")


async def download_files_from_yandex_folder(session, token, folder_url, local_folder_path):
    headers = {"Authorization": f"OAuth {token}"}
    os.makedirs(local_folder_path, exist_ok=True)
    # Получаем список файлов в папке на Яндекс.Диске
    try:
        params = {"limit": 1000}
        async with session.get(folder_url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                items = data.get("_embedded", {}).get("items", [])
                for item in items:
                    if item["type"] == "file":
                        file_name = item["name"]
                        # logger.debug(f'Загрузка {file_name}')
                        file_url = item["file"]

                        # Загружаем файл в указанную локальную папку
                        local_file_path = os.path.join(local_folder_path, file_name)
                        await download_file(session, file_url, local_file_path)
    except Exception as e:
        logger.error(f"Error downloading files from {folder_url}: {e}")


async def download_file(session, url, filename):
    headers = {'Authorization': f'OAuth {token}'}

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                async with aiofiles.open(filename, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await f.write(chunk)
            else:
                logger.error(f"Error downloading {filename} {response.status}")
    except Exception as e:
        logger.error(f"Error downloading {filename}: {e}")


async def main_parser(missing_dict):
    async with aiohttp.ClientSession() as session:
        links = [(dirname, y_path) for dirname, y_path in missing_dict.items()]
        chunk_size = 10

        for chunk in chunked(links, chunk_size):
            tasks = []

            for dirname, y_path in chunk:
                new_folder = os.path.join(all_badge, y_path.replace("disk:/Компьютер HOME-PC/База значков/", ''))
                # logger.debug(new_folder)
                folder_url = f"https://cloud-api.yandex.net/v1/disk/resources?path={y_path.replace('disk:', '')}"
                tasks.append(download_files_from_yandex_folder(session, token, folder_url, new_folder))

            await asyncio.gather(*tasks)


def chunked(iterable, chunk_size):
    """Разделяет итерируемый объект на группы определенного размера."""
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i:i + chunk_size]


def get_all_folder_comp():
    all_folders = []
    for _, dirs, _ in os.walk(all_badge):
        all_folders.extend([i.lower() for i in dirs if (len(i) > 8 and i != 'Значки ШК' and i != 'Новые значки')])
    return set(all_folders)


def missing_folders():
    loop = asyncio.get_event_loop()
    result_dict = loop.run_until_complete(main_search())

    all_folders = get_all_folder_comp()

    for item in all_folders:
        try:
            del result_dict[item]
        except Exception as ex:
            pass
    missing_dict = result_dict
    return missing_dict


if __name__ == "__main__":
    # missing_dict = missing_folders()
    missing_dict = {'bongo_cat-13new-20-37': 'disk:/Компьютер HOME-PC/База '
                                             'значков/AniKoya/BONGO_CAT-13NEW-20-37',
                    'bongo_cat-13new-20-56': 'disk:/Компьютер HOME-PC/База '
                                             'значков/AniKoya/BONGO_CAT-13NEW-20-56',
                    }
    pprint(missing_dict)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_parser(missing_dict))

    # loop = asyncio.get_event_loop()
    # result_dict = loop.run_until_complete(main_search())
    # print(result_dict)
