import os
from pathlib import Path

from environs import Env
from loguru import logger

path_root = Path(__file__).resolve().parent

env = Env()
env.read_env()

token = env.str('token')

machine_name = env.str('machine_name')
dbname = env.str('dbname')
user = env.str('user')
password = env.str('password')
host = env.str('host')

all_badge = env.str('all_badge')

sticker_path_all = env.str('sticker_path_all')

acrobat_path = env.str('acrobat_path')

path_base_y_disc = '/Значки ANIKOYA  02 23'

brands_paths = {
    'AniKoya': f'{all_badge}\\AniKoya',
    'Дочке понравилось': f'{all_badge}\\Дочке понравилось',
    'POSUTA': f'{all_badge}\\POSUTA',
    'ПостерДом': f'{all_badge}\\ПостерДом',
    'Popsocket': f'{all_badge}\\Popsocket',
    'Bidjo': f'{all_badge}\\Bidjo',
}
for brand, brand_dir in brands_paths.items():
    try:
        os.makedirs(brand_dir, exist_ok=True)
    except Exception as ex:
        logger.error(ex)

bad_list = ['amazingmauricenabor-12new-6-44', 'che_guevara-44-6', 'harrypotternabor-12new-6-44',
            'rodi_deadplate-13new-2-44', 'sk-13new-1-44', 'spongebob-13new-6-44', 'tatianakosach-13new-44-1',
            'tatianakosach-13new-44-6', 'toya_kaito-13new-2-44', 'velvet_venir-13new-2-44', 'yanderirui-13new-44-1',
            'yanderirui-13new-44-6', 'zavdv-nabor-13new-6-44', 'zvezdnoenebo-13new-44-1', 'aespanabor-7new-8-37',
            'allforthegamenabor-7new-10-37', 'allforthegamenabor-7new-10-56', 'allforthegamenabor-7new-6-37',
            'allforthegamenabor-7new-6-56', 'bsd.dadzai_azushi-13new-6-37', 'bsd.dadzai_azushi-13new-6-56',
            'coldheartnabor-7new-10-37', 'coldheartnabor-7new-10-56', 'coldheartnabor-7new-6-37',
            'coldheartnabor-7new-6-56', 'doki_ny-13new-6-37', 'doki_ny-13new-6-56', 'glaza2-13new-1-37',
            'glaza2-13new-1-56', 'hask2-13new-2-56', 'initiald-13new-4-37', 'initiald-13new-4-56',
            'jojonabor-7new-10-37', 'jojonabor-7new-10-56', 'jojonabor-7new-6-37', 'jojonabor-7new-6-56',
            'justinbieber-11new-6-37', 'justinbieber-11new-6-56', 'kamilla_valieva-13new-6-37',
            'kamilla_valieva-13new-6-56', 'kang_yuna-13new-6-37', 'kang_yuna-13new-6-56',
            'kimkardashian-11new-6-37', 'kimkardashian-11new-6-56', 'kittyisnotacat-13new-6-37',
            'kittyisnotacat-13new-6-56', 'maiorgromnabor-7new-10-37', 'maiorgromnabor-7new-10-56',
            'maiorgromnabor-7new-6-37', 'maiorgromnabor-7new-6-56', 'minecraft-nabor-7new-10-37',
            'minecraft-nabor-7new-10-56', 'minecraft-nabor-7new-6-37', 'minecraft-nabor-7new-6-56',
            'newjeans8-13new-6-37', 'newjeans8-13new-6-56', 'nydragon_simvol-13new-6-37',
            'nydragon_simvol-13new-6-56', 'omori_hero-13new-6-37', 'omori_hero-13new-6-56',
            'papini.dochki-13new-6-37', 'papini.dochki-13new-6-56', 'pokrov3-13new-6-37', 'pokrov3-13new-6-56',
            'pomni-13new-8-37', 'pomni-13new-8-56', 'pyro_genshini-13new-6-37', 'pyro_genshini-13new-6-56',
            'rojdestwo-13new-6-37', 'rojdestwo-13new-6-56', 'sekaiproject-11new-6-37', 'sekaiproject-11new-6-56',
            'seohaebom-13new-6-37', 'seohaebom-13new-6-56', 'sindromvosmiklassnika-6-37',
            'sindromvosmiklassnika-6-56', 'socialpath_sk-13new-6-56', 'spidermannabor-7new-10-37',
            'spidermannabor-7new-10-56', 'taylorswift-11new-6-37', 'taylorswift-11new-6-56',
            'tomorrowxtogether-8new-10-37', 'tomorrowxtogether-8new-10-56', 'tomorrowxtogether-8new-6-37',
            'tomorrowxtogether-8new-6-56', 'vipysknik_starsheigroup-11new-6-37',
        'vipysknik_starsheigroup-11new-6-56', 'vinil.skrech-13new-6-37', 'vinil.skrech-13new-6-56']
