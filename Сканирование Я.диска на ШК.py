import asyncio
import os
from urllib.parse import quote

import aiofiles
import aiohttp
import pandas as pd
from loguru import logger

from config import token
from utils import df_in_xlsx

OUTPUT_FOLDER = 'E:\\База значков\\Значки ШК'

semaphore = asyncio.Semaphore(10)


async def traverse_yandex_disk(session, folder_path, result_dict, progress=None):
    url = f"https://cloud-api.yandex.net/v1/disk/resources?path={quote(folder_path)}&limit=1000"
    headers = {"Authorization": f"OAuth {token}"}
    try:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            tasks = []
            for item in data["_embedded"]["items"]:
                if item["type"] == "file" and item["name"].endswith(".pdf"):
                    if not os.path.exists(os.path.join(OUTPUT_FOLDER, item["name"])):
                        print(item["name"])
                        result_dict[item["name"].lower()] = item["path"]
                elif item["type"] == "dir":
                    task = traverse_yandex_disk(session, item["path"], result_dict, progress)
                    tasks.append(task)
            if tasks:
                await asyncio.gather(*tasks)
    except Exception as ex:
        logger.debug(f'Ошибка при поиске папки {folder_path} {ex}')


async def main_search(self=None):
    logger.debug('Сканирую Яндекс диск...')
    folder_path = '/Значки ANIKOYA  02 23'
    result_dict = {}
    async with aiohttp.ClientSession() as session:
        await traverse_yandex_disk(session, folder_path, result_dict)

    df = pd.DataFrame(list(result_dict.items()), columns=['Имя', 'Путь'])
    logger.info('Создан документ Пути к артикулам.xlsx')
    df_in_xlsx(df, 'Пути к артикулам')

    return True


async def get_download_link(session, token, file_path):
    headers = {"Authorization": f"OAuth {token}"}
    url = "https://cloud-api.yandex.net/v1/disk/resources/download"
    params = {"path": file_path}

    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data["href"]
            else:
                return None
    except asyncio.TimeoutError:
        print(f"Время ожидания ответа от сервера истекло для файла '{file_path}'.")
        return None


async def download_file(session, url, filename):
    headers = {'Authorization': f'OAuth {token}'}

    async with semaphore:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    full_path = os.path.join(OUTPUT_FOLDER, filename)
                    async with aiofiles.open(full_path, 'wb') as f:
                        print(f'Загрузка {filename}')
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            await f.write(chunk)
        except Exception as e:
            print(f"Error downloading {filename}: {e}")


async def main():
    excel_file = pd.read_excel('Файлы связанные с заказом\\Пути к артикулам.xlsx')
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        tasks = []
        batch_size = 1000
        current_batch = []

        for index, row in excel_file.iterrows():
            filename = row['Имя']
            yandex_disk_path = row['Путь']
            if not filename in os.listdir(OUTPUT_FOLDER):

                # Получите ссылку для скачивания файла
                download_link = await get_download_link(session, token, yandex_disk_path)
                if download_link:
                    # Добавьте ссылку и имя файла в текущую партию
                    current_batch.append((download_link, filename))

                    # Если текущая партия достигла размера batch_size, создайте задачи для скачивания
                    if len(current_batch) >= batch_size:
                        download_tasks = [download_file(session, link, name) for link, name in current_batch]
                        tasks.extend(download_tasks)
                        current_batch = []

        # Завершите оставшиеся задачи для скачивания
        download_tasks = [download_file(session, link, name) for link, name in current_batch]
        tasks.extend(download_tasks)

        # Запустите задачи для скачивания файлов
        await asyncio.gather(*tasks)


async def async_main():
    loop = asyncio.get_event_loop()
    await main_search()


if __name__ == "__main__":
    asyncio.run(async_main())
    asyncio.run(main())
