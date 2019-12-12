from variables import PLAYOFF_PATH
from pyquery import PyQuery as pq
from collections import defaultdict
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from src.download import DownloadManager, File

# Generate the phases we want to query
FINAL = 'POT_FINAL'
SEMIFINAL = 'POT_1/2'
QUARTER_FINALS = 'POT_1/4'

# Project mapper from lengua to acbanalytics
PLAYOFF_NAME_MAPPER = {
    FINAL: 'final',
    SEMIFINAL: 'semifinal',
    QUARTER_FINALS: 'quarter_finals',
}


def open_or_download_lengua(phase, season_year, download_manager):
    """
    Open or download the lengua webpage for a given season and phase.
    :param phase:
    :param season:
    :return:
    """
    season_lengua_year = season_year + 1  # they refer the season 2017-2018 as 2018
    url = 'http://www.linguasport.com/baloncesto/nacional/liga/seekff_esp.asp?'
    url += f"s1=&s2=&saddtime1={season_lengua_year}&saddtime2={season_lengua_year}&sround1={phase}&sround2={phase}"
    url += '&sphase=PO&teambis1=&teambis2=&steamnamex1=&steamnamex2=&sscorebis=&seek=BUSCAR'
    filename = f"{PLAYOFF_PATH}/{season_year}-{PLAYOFF_NAME_MAPPER[phase]}.html"
    file = File(filename)
    return file.open_or_download(url=url, download_manager=download_manager)


def proccess_lengua(content):
    """
    Extracts the games from the lengua playoff

    Returns all the games of the phase and season in the format (home_team, away_team)
    :param content:
    :return:
    """
    phase_games = set()
    doc = pq(content)
    games = doc("tr[class='itemstyle']")

    for game in games.items():
        rows = list(game('div').items())
        home_team = rows[3].text()
        away_team = rows[4].text()
        phase_games.add((home_team, away_team))

    return phase_games


def convert_to_teams_ids(games, season):
    """
    Converts the lengua team names to acb team ids using fuzzy search
    :param games:
    :param season:
    :return:
    """
    teams = season.teams
    # Revert dict (name -> id)
    teams = {v: k for k, v in teams.items()}
    teams_names = list(teams.keys())

    actual_games = list()
    for (team_1, team_2) in games:
        if team_1 == 'Blu:Sens Obradoiro CAB':
            most_likely_coincide_1 = 'Blusens Monbus'
        elif team_1 == 'CB Aunacable Gran Canaria':
            most_likely_coincide_1 = 'Auna'
        elif team_1 == 'Pamesa Valencia BC':
            most_likely_coincide_1 = 'Pamesa Cerámica'
        else:
            most_likely_coincide_1, threshold_1 = process.extractOne(team_1, teams_names, scorer=fuzz.token_set_ratio)

        if team_2 == 'Blu:Sens Obradoiro CAB':
            most_likely_coincide_2 = 'Blusens Monbus'
        elif team_2 == 'CB Aunacable Gran Canaria':
            most_likely_coincide_2 = 'Auna'
        elif team_2 == 'Pamesa Valencia BC':
            most_likely_coincide_2 = 'Pamesa Cerámica'
        else:
            most_likely_coincide_2, threshold_2 = process.extractOne(team_2, teams_names, scorer=fuzz.token_set_ratio)
        assert threshold_1 > 70 and threshold_2 > 70, f"the threshold is too low {team_1}: {most_likely_coincide_1} {team_2}: {most_likely_coincide_2}, {teams}"

        team_1_id = teams[most_likely_coincide_1]
        team_2_id = teams[most_likely_coincide_2]
        actual_games.append((team_1_id, team_2_id))
    return actual_games


def get_playoff_games(season=None):
    """
    Gets the playoff games over a given season (or all the seasons)
    :param season:
    :return:
    """
    def get_phase_games(results, phase, season):
        season_year = season.season
        content = open_or_download_lengua(phase=phase, season_year=season_year, download_manager=dm)
        games = proccess_lengua(content=content)
        games = convert_to_teams_ids(games=games, season=season)
        for i in games:
            results[season_year][i] = PLAYOFF_NAME_MAPPER[phase]
    if not season:
        # Generates the seasons
        FIRST_SEASON = 1998
        LAST_SEASON = 2018
        seasons = range(FIRST_SEASON, LAST_SEASON + 1)
    else:
        seasons = [season]

    # Download manager object
    dm = DownloadManager()
    results = defaultdict(dict)
    for season in seasons:
        get_phase_games(results, phase=QUARTER_FINALS, season=season)
        get_phase_games(results, phase=SEMIFINAL, season=season)
        get_phase_games(results, phase=FINAL, season=season)
    return results



