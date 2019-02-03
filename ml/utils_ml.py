import os, re, logging,difflib
import numpy as np
from src.download import validate_dir, open_or_download,download,get_page
import pandas as pd
from pyquery import PyQuery as pq
from models.team import TeamName


BASE_URL = 'http://www.acb.com/'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_journey_matches(season):
    filename = os.path.join(season.SEASON_PATH, 'current_journey_calendar.html')
    url = BASE_URL + "resulcla.php"
    content = download(file_path=filename, url=url)

    return create_journey_df(content)


def get_next_journey_matches(season):
    current_journey=season.get_current_journey()

    filename = os.path.join(season.SEASON_PATH, 'next_journey_calendar.html')
    url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(season.season_id, current_journey+1)
    content = download(file_path=filename, url=url)

    return create_journey_df(content)


def get_journey_matches(season, journey):
    filename = os.path.join(season.SEASON_PATH, 'journey_{}_calendar.html').format(journey)
    url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(season.season_id, journey)
    content = download(file_path=filename, url=url)

    return create_journey_df(content)


def create_journey_df(content):
    doc = pq(content)

    matches = doc('.resultados')
    columns = ["team_home", "team_home_id", "team_away", "team_away_id"]

    df = pd.DataFrame(columns=columns)

    for tr in matches('tr').items():  # iterate over each row
        if tr('.naranjaclaro'):  # header
            team_home_txt = tr('.naranjaclaro').eq(0).text()[:-1].upper()
            team_away_txt = tr('.naranjaclaro').eq(1).text().upper()

            try:  ## In case the name of the team is exactly the same as one stated in our database for a season
                team_home_id = TeamName.get(TeamName.name == team_home_txt).team_id

            except TeamName.DoesNotExist:  ## In case there is not an exact correspondance within our database, let's find the closest match.
                query = TeamName.select(TeamName.team_id, TeamName.name)
                teams_names_ids = dict()
                for q in query:
                    teams_names_ids[q.name] = q.team_id.id

                most_likely_team = difflib.get_close_matches(team_home_txt, teams_names_ids.keys(), 1, 0.4)[0]
                team_home_id = TeamName.get(TeamName.name == most_likely_team).team_id

            try:  ## In case the name of the team is exactly the same as one stated in our database for a season
                team_away_id = TeamName.get(TeamName.name == team_away_txt).team_id

            except TeamName.DoesNotExist:  ## In case there is not an exact correspondance within our database, let's find the closest match.
                query = TeamName.select(TeamName.team_id, TeamName.name)
                teams_names_ids = dict()
                for q in query:
                    teams_names_ids[q.name] = q.team_id.id

                most_likely_team = difflib.get_close_matches(team_away_txt, teams_names_ids.keys(), 1, 0.4)[0]
                team_away_id = TeamName.get(TeamName.name == most_likely_team).team_id
                print(team_away_id)

            df = df.append({'team_home': team_home_txt, 'team_home_id': team_home_id, 'team_away': team_away_txt,
                            'team_away_id': team_away_id}, ignore_index=True)

    return df


