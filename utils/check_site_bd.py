import asyncio
import json
import time

import aiohttp
from loguru import logger

from api_rest import get_products

headers = {"Content-Type": "application/json"}
# domain = 'http://127.0.0.1:8000/api_rest'
domain = "https://mycego.online/api_rest"


async def fetch(session, semaphore, url):
    async with semaphore:
        async with session.get(url) as response:
            return await response.json()


async def get_info_publish_folder(semaphore, public_url, art):
    result_data = {}
    stickers = []
    images = []
    skin = []
    other = []

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={public_url}&fields=_embedded&limit=1000"
        ) as res:
            if res.status == 200:
                data = await res.json()
                items = data.get("_embedded", {}).get("items", [])

                for i in items:
                    file_name = i.get("name", None)
                    if (
                        file_name.endswith(".pdf")
                        and "изображения" not in file_name.lower()
                    ):
                        stickers.append(file_name)
                    elif "подложка" in file_name.lower():
                        skin.append(file_name)
                    elif (
                        file_name.endswith(".png") or file_name.endswith(".jpg")
                    ) and file_name.split(".")[0].isdigit():
                        images.append(file_name)
                    else:
                        other.append(file_name)

                result_data[f"{art} - {public_url}"] = {
                    "stickers": stickers,
                    "images": images,
                    "skin": skin,
                    "other": other,
                }
            else:
                logger.error(res.status)
                logger.error(await res.text())
            return result_data


async def process_chunk(semaphore, chunk):
    tasks = []
    for i in chunk:
        try:
            task = get_info_publish_folder(semaphore, i["directory_url"], i["art"])
            tasks.append(task)
        except Exception as ex:
            logger.error(i)
            logger.error(ex)
    return await asyncio.gather(*tasks)


async def main():
    semaphore = asyncio.Semaphore(10)
    with open(f"all_arts.json", "r", encoding="utf-8") as file:
        data = json.load(file)

    all_data = {}
    len_data = len(data)
    chunk_size = 100
    pause_duration = 3

    for chunk_start in range(0, len_data, chunk_size):
        chunk_end = min(chunk_start + chunk_size, len_data)
        chunk = data[chunk_start:chunk_end]

        print(f"Processing chunk {chunk_start + 1}-{chunk_end} / {len_data}")

        results = await process_chunk(semaphore, chunk)

        for result in results:
            all_data.update(result)

        time.sleep(pause_duration)

    with open(f"scan.json", "w", encoding="utf-8") as file:
        json.dump(all_data, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    categories = ["all"]
    bad_list = []
    bad_list_art = []
    data = get_products(categories)
    # with open(f'all_arts.json', 'w', encoding='utf-8') as file:
    #     json.dump(data, file, indent=4, ensure_ascii=False)
    # print(len(data))
    # asyncio.run(main())

    # Запрос к серверу
    # categories = ['Значки', 'Попсокеты']
    # data = get_products(categories)
    # with open(f'all_arts.json', 'w', encoding='utf-8') as file:
    #     json.dump(data, file, indent=4, ensure_ascii=False)
    # pprint(len(data))

    # Проверка на наличик стикеров
    # with open(f'all_arts.json', 'r', encoding='utf-8') as file:
    #     data = json.load(file)
    # for i in data:
    #     if not i.get('sticker'):
    #         bad_list_art.append(f'{i["art"]} - https://mycego.online/base/product/{i["id"]}/')
    # print(len(bad_list))
    # print('\n'.join(bad_list_art))

    # Получение метаданных из папок артикулов
    # with open(f'all_arts.json', 'r', encoding='utf-8') as file:
    #     data = json.load(file)
    # all_data = {}
    # len_data = len(data)
    # for index, i in enumerate(data, start=1):
    #     try:
    #         print(f'{index}/{len_data}')
    #         result = get_info_publish_folder(i['directory_url'], i['art'])
    #         print(result)
    #         all_data.update(result)
    #
    #     except Exception as ex:
    #         logger.error(i)
    #         logger.error(ex)
    #
    # with open(f'scan.json', 'w', encoding='utf-8') as file:
    #     json.dump(all_data, file, indent=4, ensure_ascii=False)

    # Проверка на наличик стикеров и других файлов
    with open(f"scan.json", "r", encoding="utf-8") as file:
        data = json.load(file)
    # for key, value in data.items():
    #     skin = value.get('skin', None)
    #     images = value.get('images', None)
    #     if skin and images:
    #         if not skin:
    #             logger.error(f'Нет подложки{key}')
    #         if not images:
    #             logger.error(f'Нет изображений {key}')
    #         # if not value.get('stickers'):
    #         #     logger.error(f'Нет ШК {key}')
    #     else:
    #         logger.error(key)
