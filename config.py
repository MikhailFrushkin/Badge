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
Bidjo_path = env.str('Bidjo_path')

sticker_path_all = env.str('sticker_path_all')

acrobat_path = env.str('acrobat_path')

path_base_y_disc = '/Значки ANIKOYA  02 23'
