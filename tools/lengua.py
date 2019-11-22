from src.download import open_or_download
from variables import PLAYOFF_PATH
from pyquery import PyQuery as pq
from collections import defaultdict

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




def open_or_download_lengua(phase, season):
    """
    Open or download the lengua webpage for a given season and phase.
    :param phase:
    :param season:
    :return:
    """
    url = 'http://www.linguasport.com/baloncesto/nacional/liga/seekff_esp.asp?'
    url += f"s1=&s2=&saddtime1={season}&saddtime2={season}&sround1={phase}&sround2={phase}"
    url += '&sphase=PO&teambis1=&teambis2=&steamnamex1=&steamnamex2=&sscorebis=&seek=BUSCAR'
    filename = f"{PLAYOFF_PATH}/{season}-{PLAYOFF_NAME_MAPPER[phase]}.html"
    return open_or_download(file_path=filename, url=url)


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


def get_playoff_games(season=None):
    """
    Gets the playoff games over a given season (or all the seasons)
    :param season:
    :return:
    """
    def get_phase_games(results, phase, season):
        content = open_or_download_lengua(phase, season)
        games = proccess_lengua(content)
        for i in games:
            results[season][i] = PLAYOFF_NAME_MAPPER[phase]

    if not season:
        # Generates the seasons
        FIRST_SEASON = 1998
        LAST_SEASON = 2018
        seasons = range(FIRST_SEASON, LAST_SEASON + 1)
    else:
        seasons = [season]

    results = defaultdict(dict)
    for season in seasons:
        get_phase_games(results, phase=QUARTER_FINALS, season=season)
        get_phase_games(results, phase=SEMIFINAL, season=season)
        get_phase_games(results, phase=FINAL, season=season)
    return results