import os

from loguru import logger
import requests

import requests
from loguru import logger

from config import token


def get_file_excel():
    headers = {
        "Authorization": f"OAuth {token}"
    }

    params = {
        "path": 'Отчеты',
        "fields": "_embedded.items"
    }

    response = requests.get("https://cloud-api.yandex.net/v1/disk/resources", headers=headers, params=params)

    if response.status_code == 200:
        files = response.json().get('_embedded', {}).get('items', None)
        result = [(i['name'], i['file']) for i in files]
        return result
    else:
        logger.error("Error:", response.status_code)


def download_file(destination_path, url):
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(destination_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:  # filter out keep-alive new chunks
                        file.write(chunk)
            logger.info(f"File downloaded successfully: {destination_path}")
        else:
            logger.error(f"Error {response.status_code} while downloading file: {url}")
    except requests.RequestException as e:
        logger.error(f"Error during downloading file: {e}")


if __name__ == '__main__':
    directory = 'temp_excel'
    os.makedirs(directory, exist_ok=True)
    files = get_file_excel()
    for name, url in files:
        destination_path = os.path.join(directory, name)
        download_file(destination_path, url)

