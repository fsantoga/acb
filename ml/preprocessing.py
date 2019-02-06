import os, re, logging,difflib,datetime
from src.download import validate_dir, open_or_download,download,get_page
import pandas as pd
from pyquery import PyQuery as pq
from models.team import TeamName
from tqdm import tqdm
from datetime import date, timedelta

BASE_URL = 'http://www.acb.com/'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_prev_matches_numbers(date_start, date_end, team_id, df):
    dfteam_previous = df[((df["team_home_id"]==team_id) | (df["team_away_id"]==team_id)) & (df["kickoff_time"]<date_end) & (df["kickoff_time"]>date_start)].copy()
    if len(dfteam_previous) == 0:
        win_rate = 0.
        score_diff_avg = 0.
    else:
        dfteam_previous["score_team"] = dfteam_previous.apply(lambda x: x["score_home"] if x["team_home_id"]==team_id else x["score_away"], axis=1)
        dfteam_previous["score_oponent"] = dfteam_previous.apply(lambda x: x["score_away"] if x["team_home_id"]==team_id else x["score_home"], axis=1)
        dfteam_previous["won"] = dfteam_previous["score_team"] > dfteam_previous["score_oponent"]
        dfteam_previous["score_diff"] = dfteam_previous["score_team"] - dfteam_previous["score_oponent"]
        win_rate = float(dfteam_previous["won"].sum()) / len(dfteam_previous)
        score_diff_avg = dfteam_previous["score_diff"].mean()
    return win_rate, score_diff_avg


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


def calculate_variables_last_X_train(df_games, last_X_days):
    # for each game add results of last ones
    win_rate_home_list = []
    win_rate_away_list = []
    score_diff_avg_home_list = []
    score_diff_avg_away_list = []
    for i, row in tqdm(df_games.iterrows()):
        date_end = row["kickoff_time"]
        date_start = date_end - timedelta(days=last_X_days)
        # For the home team
        team_id = row["team_home_id"]
        # print("Home team:", team_id)
        win_rate_home, score_diff_avg_home = get_prev_matches_numbers(date_start, date_end, team_id, df_games)
        win_rate_home_list += [win_rate_home]
        score_diff_avg_home_list += [score_diff_avg_home]
        # For the away team
        team_id = row["team_away_id"]
        # print("Away team:", team_id)
        win_rate_away, score_diff_avg_away = get_prev_matches_numbers(date_start, date_end, team_id, df_games)
        win_rate_away_list += [win_rate_away]
        score_diff_avg_away_list += [score_diff_avg_away]

    # add historical to df
    df_games["win_rate_home_last"+str(last_X_days)] = win_rate_home_list
    df_games["score_diff_avg_home_last"+str(last_X_days)] = score_diff_avg_home_list
    df_games["win_rate_away_last"+str(last_X_days)] = win_rate_away_list
    df_games["score_diff_avg_away_last"+str(last_X_days)] = score_diff_avg_away_list

    return df_games

def calculate_variables_last_X_predict(df_predict, df_games, last_X_days):
    # for each game add results of last ones
    win_rate_home_list = []
    win_rate_away_list = []
    score_diff_avg_home_list = []
    score_diff_avg_away_list = []
    for i, row in tqdm(df_predict.iterrows()):
        date_end = row["kickoff_time"]
        date_start = date_end - timedelta(days=last_X_days)
        # For the home team
        team_id = row["team_home_id"]
        # print("Home team:", team_id)
        win_rate_home, score_diff_avg_home = get_prev_matches_numbers(date_start, date_end, team_id, df_games)
        win_rate_home_list += [win_rate_home]
        score_diff_avg_home_list += [score_diff_avg_home]
        # For the away team
        team_id = row["team_away_id"]
        # print("Away team:", team_id)
        win_rate_away, score_diff_avg_away = get_prev_matches_numbers(date_start, date_end, team_id, df_games)
        win_rate_away_list += [win_rate_away]
        score_diff_avg_away_list += [score_diff_avg_away]

    # add historical to df
    df_predict["win_rate_home_last" + str(last_X_days)] = win_rate_home_list
    df_predict["score_diff_avg_home_last" + str(last_X_days)] = score_diff_avg_home_list
    df_predict["win_rate_away_last" + str(last_X_days)] = win_rate_away_list
    df_predict["score_diff_avg_away_last" + str(last_X_days)] = score_diff_avg_away_list

    return df_predict


def get_next_journey(season):
    current_journey=season.get_current_journey()

    filename = os.path.join(season.SEASON_PATH, 'last_calendar.html')
    url = BASE_URL + "proxjornadas.php".format(season.season_id, current_journey+1)
    content = download(file_path=filename, url=url)

    return create_next_journey_df(content, season.season)


def create_next_journey_df(content, season):
    doc = pq(content)

    matches = doc('.jornadas').eq(0)
    columns = ["team_home", "team_home_id", "team_away", "team_away_id", "season", "kickoff_time"]

    df = pd.DataFrame(columns=columns)

    #extract journey number
    titulo_prox = doc('.tituloprox').eq(0).text().upper()
    journey = titulo_prox.split(' ')
    journey=journey[5]

    for tr in matches('tr').items():  # iterate over each row
            if tr('.oscuro2'):  # header
                teams = tr('.oscuro2').eq(0).text().upper()
                teams_names=teams.split('-')
                team_home_txt=teams_names[0]
                team_away_txt=teams_names[1]
                #print(teams)
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


                date = tr('.claro').eq(0).text()
                date=date.split(' ')[1]

                hour = tr('.oscuro').eq(0).text()
                time=hour.split(' ')[0]

                day, month, year = list(map(int, date.split("/")))
                hour, minute = list(map(int, time.split(":")))
                kickoff_time = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
                #print(kickoff_time)

                df = df.append({ 'team_home': team_home_txt,'team_home_id': team_home_id.id,'team_away_id': team_away_id.id,'team_away': team_away_txt,'kickoff_time': kickoff_time,'season':season,'journey': journey}, ignore_index=True)

    return df

def get_journeys(season, number_journeys):
    current_journey=season.get_current_journey()

    filename = os.path.join(season.SEASON_PATH, 'last_calendar.html')
    url = BASE_URL + "proxjornadas.php".format(season.season_id, current_journey+1)
    content = download(file_path=filename, url=url)

    return create_journeys_df(content, number_journeys, season.season)

def create_journeys_df(content, number_journeys, season):
    doc = pq(content)

    columns = ["team_home", "team_home_id", "team_away", "team_away_id", "season", "kickoff_time"]

    df = pd.DataFrame(columns=columns)

    for i in range(0,number_journeys):
        matches = doc('.jornadas').eq(i)

        # extract journey number
        titulo_prox = doc('.tituloprox').eq(i).text().upper()
        journey = titulo_prox.split(' ')
        journey = journey[5]

        for tr in matches('tr').items():  # iterate over each row
            if tr('.oscuro2'):  # header
                teams = tr('.oscuro2').eq(0).text().upper()
                teams_names = teams.split('-')
                team_home_txt = teams_names[0]
                team_away_txt = teams_names[1]
                # print(teams)
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

                date = tr('.claro').eq(0).text()
                date = date.split(' ')[1]

                hour = tr('.oscuro').eq(0).text()
                time = hour.split(' ')[0]

                day, month, year = list(map(int, date.split("/")))
                hour, minute = list(map(int, time.split(":")))
                kickoff_time = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)
                # print(kickoff_time)

                df = df.append(
                    {'team_home': team_home_txt, 'team_home_id': team_home_id.id, 'team_away_id': team_away_id.id,
                     'team_away': team_away_txt, 'kickoff_time': kickoff_time, 'season': season, 'journey': journey},
                    ignore_index=True)

    return df

