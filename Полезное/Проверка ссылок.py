import pandas as pd
import requests
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
from utils import df_in_xlsx

count = 0


def process_link(link):
    global count
    count += 1
    try:
        url = f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={link}"
        response = requests.get(url)
        print(count, response.status_code)

        data = response.json()
        if "items" not in data['_embedded']:
            pass
    except Exception as ex:
        logger.error(f'{link} {ex}')
        return link
    return None


def get_yandex_disk_files():
    df = pd.read_excel('E:\\ANIKOYA - Общий отчет дизайнеров.xlsx', sheet_name='2023')
    print(len(df))
    link_list = df['Ссылка на папку'].tolist()
    # bad_list = []
    # for index, i in enumerate(link_list):
    #     print(index)
    #     try:
    #         url = f"https://cloud-api.yandex.net/v1/disk/public/resources?public_key={i}"
    #         response = requests.get(url)
    #         data = response.json()
    #         if "items" not in data['_embedded']:
    #             pass
    #     except Exception as ex:
    #         logger.error(f'{i} {ex}')
    #         bad_list.append(i)
    #
    # df_filtered = df[df['Ссылка на папку'].isin(bad_list)]
    # df_in_xlsx(df_filtered, 'Не рабочие ссылки Все')
    bad_links = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(process_link, link_list)
        bad_links = [link for link in results if link is not None]

    df_filtered = df[df['Ссылка на папку'].isin(bad_links)]
    df_in_xlsx(df_filtered, 'Не рабочие ссылки Anikoya')


if __name__ == '__main__':
    get_yandex_disk_files()
