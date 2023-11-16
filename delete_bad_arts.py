import asyncio
import shutil
from urllib.parse import quote

import aiohttp
from loguru import logger
from peewee import fn

from config import token
from db import Article


async def traverse_yandex_disk(session, folder_path, list_arts, offset=0):
    url = f"https://cloud-api.yandex.net/v1/disk/resources?path={quote(folder_path)}&limit=100&offset={offset}"
    headers = {"Authorization": f"OAuth {token}"}

    try:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            for item in data["_embedded"]["items"]:
                list_arts.append(item["name"].lower())
    except Exception as ex:
        logger.debug(f'Ошибка при поиске папки {folder_path} {ex}')


async def main_search():
    folder_path = '/Компьютер HOME-PC/Исправить'
    list_arts = []
    async with aiohttp.ClientSession() as session:
        await traverse_yandex_disk(session, folder_path, list_arts)
    return list_arts


def delete_arts():
    loop = asyncio.get_event_loop()
    list_arts = loop.run_until_complete(main_search())
    if list_arts:
        results = Article.select().where(fn.Lower(Article.art).in_(list_arts))
        for article in results:
            try:
                print(f'Удален {article.art}')
                article.delete_instance()
                shutil.rmtree(article.folder)
            except Exception as ex:
                logger.error(ex)


if __name__ == "__main__":
    delete_arts()
