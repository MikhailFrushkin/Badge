from pathlib import Path

from environs import Env

path_root = Path(__file__).resolve().parent

env = Env()
env.read_env()

token = env.str('token')

anikoya_path = env.str('anikoya_path')
dp_path = env.str('dp_path')

sticker_path_all = env.str('sticker_path_all')
sticker_path1 = env.str('sticker_path1')
sticker_path2 = env.str('sticker_path2')
sticker_path3 = env.str('sticker_path3')

acrobat_path = env.str('acrobat_path')

google_sticker_path1 = env.str('google_sticker_path1')
google_sticker_path2 = env.str('google_sticker_path2')
google_sticker_path3 = env.str('google_sticker_path3')

id_google_table_DP = env.str('id_google_table_DP')
id_google_table_anikoya = env.str('id_google_table_anikoya')

