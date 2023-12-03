import asyncio
import os
from pathlib import Path

import aiohttp
from loguru import logger

from blur import blur_image
from config import token, all_badge
from db import GoogleTable

semaphore = asyncio.Semaphore(3)


async def get_yandex_disk_files(session, token, public_link):
    arts_dict = {}
    headers = {"Authorization": f"OAuth {token}"}
    url = "https://cloud-api.yandex.net/v1/disk/public/resources"
    path = '/'
    stack = [(public_link, path)]
    while stack:
        current_folder_path, path = stack.pop()
        params = {"public_key": current_folder_path, "limit": 1000, "path": path}
        while True:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    files = data['_embedded']["items"]
                    if files:
                        files_on_yandex_disk = []
                        art = None

                        for item in files:
                            if item["type"] == "dir":
                                stack.append((public_link, item["path"]))
                            elif item["type"] == "file":
                                file_name = item["name"]
                                file_path = item["path"]
                                if ('поп' in file_name.lower()
                                        and '1' in file_name
                                        and file_name.lower().endswith(('.png', '.jpg'))):
                                    files_on_yandex_disk.append(('Подложка.png', file_path))
                                elif file_name.replace(' ', '').strip()[0].isdigit():
                                    files_on_yandex_disk.append((file_name, file_path))
                                elif file_name.endswith('.pdf'):
                                    art = file_name.replace('.pdf', '').strip()
                        if art and len(files_on_yandex_disk) == 2:
                            arts_dict[art] = files_on_yandex_disk
                            arts_dict['url'] = public_link
                        else:
                            logger.error(f'Нет шк для артикула {public_link}')
                        if "offset" in data['_embedded']:
                            params["offset"] = data['_embedded']["offset"] + data['_embedded']["limit"]
                        else:
                            break
                    else:
                        break
                else:
                    raise RuntimeError(f"Ошибка при получении файлов: {response.status}")

    logger.success(f'Найденно новых артикулов: {len(arts_dict)}')
    return arts_dict


async def get_download_links(session, token, arts_dict):
    headers = {"Authorization": f"OAuth {token}"}
    download_links = {}
    public_url = arts_dict['url']

    for art, files in arts_dict.items():
        if isinstance(files, list):
            download_links[art] = []
            for file_name, file_path in files:
                download_url = await get_file_download_link(session, headers, public_url, file_path)
                download_links[art].append((file_name, download_url))
    return download_links


async def get_file_download_link(session, headers, public_url, file_path):
    url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    params = {"public_key": public_url, "path": file_path}
    async with session.get(url, headers=headers, params=params) as response:
        if response.status == 200:
            data = await response.json()
            return data["href"]
        else:
            raise RuntimeError(f"Ошибка при получении ссылки на скачивание: {response.status}")


async def download_file(session, token, file_url, local_path):
    headers = {"Authorization": f"OAuth {token}"}

    async with session.get(file_url, headers=headers) as response:
        if response.status == 200:
            data = await response.read()
            with open(local_path, "wb") as local_file:
                local_file.write(data)
            print(f"Файл успешно загружен: {local_path}")
        else:
            raise RuntimeError(f"Ошибка при загрузке файла: {response.status}")


async def process_arts_dict(session, token, arts_dict, local_base_path):
    for art, files in arts_dict.items():
        for file_name, file_url in files:
            local_path = os.path.join(local_base_path, art, file_name)
            await download_file(session, token, file_url, local_path)


async def scan_files(public_urls):
    pop_path = f'{all_badge}\\Popsockets'
    os.makedirs(pop_path, exist_ok=True)
    for public_url in public_urls:
        try:
            async with aiohttp.ClientSession() as session:
                arts_dict = await get_yandex_disk_files(session, token, public_url.folder_link)
                if arts_dict:
                    try:
                        download_links = await get_download_links(session, token, arts_dict)
                        try:
                            for art in download_links.keys():
                                local_art_path = os.path.join(pop_path, art)
                                Path(local_art_path).mkdir(parents=True, exist_ok=True)
                            await process_arts_dict(session, token, download_links, pop_path)

                            for art in download_links.keys():
                                try:
                                    path_dir = os.path.join(pop_path, art)
                                    for file in os.listdir(path_dir):
                                        file_path = os.path.join(path_dir, file)
                                        if os.path.isfile(file_path) and file[0].isdigit():
                                            blur_image(file_path, file_path, 44)
                                except Exception as ex:
                                    logger.error(f'Ошибка  {ex}')
                        except Exception as ex:
                            logger.error(f'Ошибка  {ex}')
                    except Exception as ex:
                        logger.error(f'Ошибка  {ex}')
        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")
        finally:
            public_url.status_download = True
            public_url.save()


def get_stack():
    records = GoogleTable.select().where(~GoogleTable.status_download)
    print(len(records))


if __name__ == "__main__":
    asyncio.run(scan_files())
