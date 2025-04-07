import asyncio
import os

import aiohttp

from config import token


async def upload_file(session, file_path, destination_path):
    upload_url = "https://cloud-api.yandex.net/v1/disk/resources/upload"

    headers = {
        "Authorization": f"OAuth {token}"
    }

    params = {
        "path": destination_path,
        "overwrite": "true"
    }

    async with session.get(upload_url, headers=headers, params=params) as response:
        upload_data = await response.json()

        if "href" in upload_data:
            async with session.put(upload_data["href"], data=open(file_path, "rb")) as upload_response:
                if upload_response.status == 201:
                    pass
                    # print(f"Файл {destination_path} успешно загружен")
                else:
                    print(f"Произошла ошибка при загрузке файла {destination_path}: {upload_response.text}")
        else:
            print(f"Произошла ошибка при получении URL для загрузки файла {destination_path}: {upload_data}")


async def upload_statistic_files_async(order=None):
    """Отправка на я.диск файла с ненайденными артикулами"""
    current_directory = os.getcwd()
    directory = os.path.join(current_directory, 'Файлы связанные с заказом')
    if os.path.exists(directory) and len(os.listdir(directory)) > 0:
        tasks = []

        async with aiohttp.ClientSession() as session:
            for file in os.listdir(directory):
                if order in file:
                    file_path = os.path.join(directory, file)
                    destination_path = f"/Отчеты/{file}"
                    task = upload_file(session, file_path, destination_path)
                    tasks.append(task)

            await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(upload_statistic_files_async())
