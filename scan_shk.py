import asyncio
import datetime
import json
import os
from urllib.parse import quote

import aiofiles
import aiohttp
from loguru import logger

from config import token, sticker_path_all

headers = {'Authorization': f'OAuth {token}'}
result_dict = {}


async def traverse_yandex_disk(session, folder_path, offset=0):
    limit = 1000
    url = (f"https://cloud-api.yandex.net/v1/disk/resources?path={quote(folder_path)}"
           f"&limit={limit}&offset={offset}"
           f"&fields=_embedded.items.name,_embedded.items.type,_embedded.items.size,"
           f"_embedded.items.path,_embedded.offset,_embedded.total")
    try:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            tasks = []
            for item in data["_embedded"]["items"]:
                if item["type"] == "file" and item["name"].endswith(".pdf") and item['size'] < 30000:
                    result_dict[item["name"].lower().strip()] = item["path"]
                elif item["type"] == "dir":
                    task = traverse_yandex_disk(session, item["path"])  # Рекурсивный вызов
                    tasks.append(task)
            if tasks:
                await asyncio.gather(*tasks)  # Дождемся завершения всех рекурсивных вызовов

            total = data["_embedded"]["total"]
            offset += limit
            # logger.warning(f'Просканировано: {offset}')
            if offset < total:
                await traverse_yandex_disk(session, folder_path, offset=offset)

    except Exception as ex:
        logger.error(f'Ошибка при поиске папки {folder_path} {ex}')


async def main_search():
    folder_path = '/Значки ANIKOYA  02 23/Михаил/Значки ШК'
    async with aiohttp.ClientSession() as session:
        await traverse_yandex_disk(session, folder_path)


async def get_download_link(session, file_path):
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    params = {"path": file_path}

    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data["href"]
    except asyncio.TimeoutError:
        logger.error(f"Время ожидания ответа от сервера истекло для файла '{file_path}'.")


async def download_file(session, url, filename):
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                full_path = os.path.join(sticker_path_all, filename)
                async with aiofiles.open(full_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await f.write(chunk)
        logger.success(f"Загружен {filename}")
    except Exception as e:
        logger.error(f"Error downloading {filename}: {e}")


async def main_sh():
    os.makedirs(sticker_path_all, exist_ok=True)
    files_dir = [i.strip().lower() for i in os.listdir(sticker_path_all)]
    async with aiohttp.ClientSession() as session:
        tasks = []
        batch_size = 10
        current_batch = []
        with open('scan_sh.json', 'w') as f:
            json.dump(result_dict, f, indent=4, ensure_ascii=False)

        for filename, yandex_disk_path in result_dict.items():
            if not filename in files_dir:
                logger.debug(filename)
                logger.debug(yandex_disk_path)
                download_link = await get_download_link(session, yandex_disk_path)
                if download_link:
                    current_batch.append((download_link, filename))

                    if len(current_batch) >= batch_size:
                        download_tasks = [download_file(session, link, name) for link, name in current_batch]
                        tasks.extend(download_tasks)
                        current_batch = []

        # Завершите оставшиеся задачи для скачивания
        download_tasks = [download_file(session, link, name) for link, name in current_batch]
        tasks.extend(download_tasks)

        # Запустите задачи для скачивания файлов
        await asyncio.gather(*tasks)


async def async_main_sh():
    start = datetime.datetime.now()
    await main_search()
    logger.debug(f'Найдено ШК: {len(result_dict)}')
    logger.success(datetime.datetime.now() - start)
    await main_sh()
    return result_dict


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    asyncio.run(async_main_sh())
