from pathlib import Path

from environs import Env

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
anikoya_path = env.str('anikoya_path')
dp_path = env.str('dp_path')

sticker_path_all = env.str('sticker_path_all')

acrobat_path = env.str('acrobat_path')

google_sticker_path1 = env.str('google_sticker_path1')
google_sticker_path2 = env.str('google_sticker_path2')
google_sticker_path3 = env.str('google_sticker_path3')

id_google_table_DP = env.str('id_google_table_DP')
id_google_table_anikoya = env.str('id_google_table_anikoya')

path_base_y_disc = '/Значки ANIKOYA  02 23'

ready_path = r'E:\База значков\Значки ШК'