import os
from src.download import validate_dir

FIRST_SEASON = 1956
LAST_SEASON = 2018

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT_DIR, 'data')
TEAMS_PATH = os.path.join(DATA_PATH, 'teams')
ACTORS_PATH = os.path.join(DATA_PATH, 'actors')
PLAYERS_PATH = os.path.join(ACTORS_PATH, 'players')
COACHES_PATH = os.path.join(ACTORS_PATH, 'coaches')


validate_dir(DATA_PATH)
validate_dir(TEAMS_PATH)
validate_dir(ACTORS_PATH)
validate_dir(PLAYERS_PATH)
validate_dir(COACHES_PATH)
validate_dir(os.path.join(PLAYERS_PATH, 'photos'))
validate_dir(os.path.join(COACHES_PATH, 'photos'))