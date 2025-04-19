import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from loguru import logger


def get_base_dir():
    """Возвращает текущую директорию, где расположен исполняемый файл или скрипт, на уровень выше."""
    if getattr(sys, "frozen", False):
        # Если приложение собрано в exe
        return os.path.dirname(sys.executable)
    else:
        # Если приложение запущено как скрипт .py
        return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
OUTPUT_READY_FILES = os.path.join(BASE_DIR, "Файлы на печать")
load_dotenv(".env")
token = os.getenv("token")

machine_name = os.getenv("machine_name")
# Подключение к Postgres
dbname = os.getenv("dbname")
user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")

# чтение путей к папкам на локальном компе с которыми работает программа
all_badge = os.getenv("all_badge")
sticker_path_all = os.getenv("sticker_path_all")
acrobat_path = os.getenv("acrobat_path")
if not all_badge:
    logger.error("all_badge")

replace_dict = {}
# Работа с артикулами для замены, читает файл и создает словарь, при работе программы если есть в
# заказе артикул из словаря меняет его на соответствующий
try:
    if os.path.exists("Замена артикулов.xlsx"):
        df = pd.read_excel("Замена артикулов.xlsx")
        for index, row in df.iterrows():
            replace_dict[row["Артикул"].strip().upper()] = row["Замена"].strip().upper()
except Exception as ex:
    logger.error(ex)

# Папки с брендами значков
brands_paths = {
    "AniKoya": f"{all_badge}\\AniKoya",
    "Дочке понравилось": f"{all_badge}\\Дочке понравилось",
    "POSUTA": f"{all_badge}\\POSUTA",
    "ПостерДом": f"{all_badge}\\ПостерДом",
    "Popsocket": f"{all_badge}\\Popsockets",
    "Bidjo": f"{all_badge}\\Bidjo",
}
for brand, brand_dir in brands_paths.items():
    try:
        os.makedirs(brand_dir, exist_ok=True)
    except Exception as ex:
        logger.error(ex)
# Артикула которые игнорим при проверке, у них ошибки, но это норм
bad_list = [
    "amazingmauricenabor-12new-6-44",
    "che_guevara-44-6",
    "harrypotternabor-12new-6-44",
    "rodi_deadplate-13new-2-44",
    "sk-13new-1-44",
    "spongebob-13new-6-44",
    "tatianakosach-13new-44-1",
    "tatianakosach-13new-44-6",
    "toya_kaito-13new-2-44",
    "velvet_venir-13new-2-44",
    "yanderirui-13new-44-1",
    "yanderirui-13new-44-6",
    "zavdv-nabor-13new-6-44",
    "zvezdnoenebo-13new-44-1",
    "aespanabor-7new-8-37",
    "allforthegamenabor-7new-10-37",
    "allforthegamenabor-7new-10-56",
    "allforthegamenabor-7new-6-37",
    "allforthegamenabor-7new-6-56",
    "bsd.dadzai_azushi-13new-6-37",
    "bsd.dadzai_azushi-13new-6-56",
    "coldheartnabor-7new-10-37",
    "coldheartnabor-7new-10-56",
    "coldheartnabor-7new-6-37",
    "coldheartnabor-7new-6-56",
    "doki_ny-13new-6-37",
    "doki_ny-13new-6-56",
    "glaza2-13new-1-37",
    "glaza2-13new-1-56",
    "hask2-13new-2-56",
    "initiald-13new-4-37",
    "initiald-13new-4-56",
    "jojonabor-7new-10-37",
    "jojonabor-7new-10-56",
    "jojonabor-7new-6-37",
    "jojonabor-7new-6-56",
    "justinbieber-11new-6-37",
    "justinbieber-11new-6-56",
    "kamilla_valieva-13new-6-37",
    "kamilla_valieva-13new-6-56",
    "kang_yuna-13new-6-37",
    "kang_yuna-13new-6-56",
    "kimkardashian-11new-6-37",
    "kimkardashian-11new-6-56",
    "kittyisnotacat-13new-6-37",
    "kittyisnotacat-13new-6-56",
    "maiorgromnabor-7new-10-37",
    "maiorgromnabor-7new-10-56",
    "maiorgromnabor-7new-6-37",
    "maiorgromnabor-7new-6-56",
    "minecraft-nabor-7new-10-37",
    "minecraft-nabor-7new-10-56",
    "minecraft-nabor-7new-6-37",
    "minecraft-nabor-7new-6-56",
    "newjeans8-13new-6-37",
    "newjeans8-13new-6-56",
    "nydragon_simvol-13new-6-37",
    "nydragon_simvol-13new-6-56",
    "omori_hero-13new-6-37",
    "omori_hero-13new-6-56",
    "papini.dochki-13new-6-37",
    "papini.dochki-13new-6-56",
    "pokrov3-13new-6-37",
    "pokrov3-13new-6-56",
    "pomni-13new-8-37",
    "pomni-13new-8-56",
    "pyro_genshini-13new-6-37",
    "pyro_genshini-13new-6-56",
    "rojdestwo-13new-6-37",
    "rojdestwo-13new-6-56",
    "sekaiproject-11new-6-37",
    "sekaiproject-11new-6-56",
    "seohaebom-13new-6-37",
    "seohaebom-13new-6-56",
    "sindromvosmiklassnika-6-37",
    "sindromvosmiklassnika-6-56",
    "socialpath_sk-13new-6-56",
    "spidermannabor-7new-10-37",
    "spidermannabor-7new-10-56",
    "taylorswift-11new-6-37",
    "taylorswift-11new-6-56",
    "tomorrowxtogether-8new-10-37",
    "tomorrowxtogether-8new-10-56",
    "tomorrowxtogether-8new-6-37",
    "tomorrowxtogether-8new-6-56",
    "vipysknik_starsheigroup-11new-6-37",
    "vipysknik_starsheigroup-11new-6-56",
    "vinil.skrech-13new-6-37",
    "vinil.skrech-13new-6-56",
]
