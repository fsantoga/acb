import os
import re
import numpy as np
from src.download import validate_dir, open_or_download,download,get_page
from pyquery import PyQuery as pq
from utils.log import logger


FIRST_SEASON = 1956
LAST_SEASON = 2018
BASE_URL = 'http://www.acb.com/'
DATA_PATH = './data/'
TEAMS_PATH = os.path.join(DATA_PATH, 'teams/')
ACTORS_PATH = os.path.join(DATA_PATH, 'actors/')
PLAYERS_PATH = os.path.join(ACTORS_PATH, 'players/')
COACHES_PATH = os.path.join(ACTORS_PATH, 'coaches/')

validate_dir(TEAMS_PATH)
validate_dir(ACTORS_PATH)
validate_dir(PLAYERS_PATH)
validate_dir(COACHES_PATH)

from_journey = 1
to_journey = 54

PLAYOFF_MAPPER = {
    1994: [3, 5, 5],
    1995: [3, 5, 5],
    1996: [5, 5, 5],
    1997: [5, 5, 5],
    1998: [5, 5, 5],
    1999: [5, 5, 5],
    2000: [5, 5, 5],
    2001: [5, 5, 5],
    2002: [5, 5, 5],
    2003: [5, 5, 5],
    2004: [5, 5, 5],
    2005: [5, 5, 5],
    2006: [5, 5, 5],
    2007: [3, 3, 5],
    2008: [3, 3, 5],
    2009: [3, 5, 5],
    2010: [3, 5, 5],
    2011: [3, 5, 5],
    2012: [3, 5, 5],
    2013: [3, 5, 5],
    2014: [3, 5, 5],
    2015: [3, 5, 5],
    2016: [3, 5, 5],
    2017: [3, 5, 5],
    2018: [3, 5, 5],
}

class Season:
    def __init__(self, season):
        logger.info(f"Creating Season: {season}")

        self.season = season
        self.season_id = season - FIRST_SEASON + 1  # First season in 1956 noted as 1.
        self.SEASON_PATH = os.path.join(DATA_PATH, str(self.season))
        self.GAMES_PATH = os.path.join(self.SEASON_PATH, 'games')

        validate_dir(self.SEASON_PATH)
        validate_dir(self.GAMES_PATH)

        if self.season >= 2016:
            self.EVENTS_PATH = os.path.join(self.SEASON_PATH, 'events')
            self.SHOTCHART_PATH = os.path.join(self.SEASON_PATH, 'shotchart')

            validate_dir(self.EVENTS_PATH)
            validate_dir(self.SHOTCHART_PATH)

        #self.current_journey=self.get_current_journey(season)
        self.relegation_playoff_seasons = [1994, 1995, 1996, 1997]
        self.num_teams = self.get_number_teams()
        self.playoff_format = self.get_playoff_format()
        self.mismatched_teams = []

        #self.game_events_ids=self.get_game_events_ids()
        #self.game_ids=self.get_game_ids()

        #if self.season == get_current_season():
        #    self.current_game_events_ids=self.get_current_game_events_ids()

    def get_game_events_ids(self):
        game_events_ids = {}
        for i in range(from_journey, to_journey + 1):
            url = "http://jv.acb.com/historico.php?jornada={}&cod_competicion=LACB&cod_edicion={}".format(i,self.season_id)
            content = get_page(url)

            fls_ids = re.findall(r'<div class="partido borde_azul" id="partido-([0-9]+)">', content, re.DOTALL)
            game_ids = re.findall(r'"http://www.acb.com/fichas/LACB([0-9]+).php', content, re.DOTALL)
            game_events_ids.update(dict(zip(fls_ids, game_ids)))

        return game_events_ids

    def get_game_ids(self):
        game_ids_list=[]
        for i in range(from_journey, to_journey + 1):
            url = "http://jv.acb.com/historico.php?jornada={}&cod_competicion=LACB&cod_edicion={}".format(i,self.season_id)
            content = get_page(url)

            game_ids = re.findall(r'"http://www.acb.com/fichas/LACB([0-9]+).php', content, re.DOTALL)
            game_ids_list+=game_ids
        return game_ids_list

    def get_current_game_events_ids(self):
        current_game_events_ids = {}
        for i in range(from_journey, self.get_current_journey() + 1):
            url = "http://jv.acb.com/historico.php?jornada={}&cod_competicion=LACB&cod_edicion={}".format(i,self.season_id)
            content = get_page(url)

            fls_ids = re.findall(r'<div class="partido borde_azul" id="partido-([0-9]+)">', content, re.DOTALL)
            game_ids = re.findall(r'"http://www.acb.com/fichas/LACB([0-9]+).php', content, re.DOTALL)
            current_game_events_ids.update(dict(zip(fls_ids, game_ids)))

        return current_game_events_ids

    def save_teams(self):
        """
        Saves a webpage containing all the teams of the season.

        E.g.: http://www.acb.com/club/index/temporada_id/2019
        :return:
        """
        teams_filename = os.path.join(self.SEASON_PATH, 'teams.html')
        teams_url = BASE_URL + f"club/index/temporada_id/{self.season}"
        logger.info(f"Downloading teams from {teams_url}")
        return open_or_download(file_path=teams_filename, url=teams_url)

    def get_number_teams(self):
        """
        Extracts the number of teams for the season.

        Example of team:
        <a href="/club/plantilla/id/2" class="clase_mostrar_block960 equipo_logo primer_logo">
        <img src="http://static.acb.com/img/32/1d/a/1453105588.png" alt="Barça " /></a>
        :return:
        """
        content = self.save_teams()
        doc = pq(content)
        teams = doc("div[class='contenedor_logos_equipos']").items('img')
        teams = [t.attr('alt') for t in teams]

        logger.info(f"There are {len(teams)} teams: {teams}")
        return len(teams)

    def get_playoff_format(self):
        """
        Gets the playoff format of the season

        Source:
        - https://web.archive.org/web/20190403020219/http://www.acb.com/playoff.php?cod_competicion=LACB&cod_edicion=62
        - For 1994 and 1995: page 32 in http://www.acb.com/publicaciones/guia1995
        """
        logger.info(f"The playoff format is {PLAYOFF_MAPPER[self.season]}")
        return PLAYOFF_MAPPER[self.season]

    def get_teams_ids(self):
        content = self.save_teams()
        teams_doc = pq(content)
        teams_tag = '.resultados2'
        teams_info = teams_doc(teams_tag)('tr')('a')

        teams_ids = []
        for team in teams_info.items():
            id = re.search(r'id=(.*)', team.attr('href')).group(1)
            teams_ids+=[id]

        return teams_ids

    def get_number_games_regular_season(self):
        return (self.num_teams - 1) * self.num_teams

    def get_number_games_playoff(self):
        games_per_round = [4, 2, 1]  # Quarter-finals, semifinals, final.
        try:
            return sum(np.array(self.playoff_format) * np.array(games_per_round))  # Element-wise multiplication.
        except Exception as e:
            logger.info('No se ha jugado ningun partido de playoff...\n')
            #print(e)
            return 0

    def get_number_games(self):
        return self.get_number_games_regular_season() + self.get_number_games_playoff() + self.get_number_games_relegation_playoff()

    def get_number_games_relegation_playoff(self):
        return 5*2 if self.season in self.relegation_playoff_seasons else 0

    def get_relegation_teams(self):
        if self.season <= 1994:
            return {1994: ['VALVI GIRONA', 'BREOGÁN LUGO', 'PAMESA VALENCIA', 'SOMONTANO HUESCA']}[self.season]
        else:
            filename = os.path.join(self.SEASON_PATH, 'relegation_playoff.html')
            url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(self.season_id, (self.get_number_teams()-1)*2)
            content = open_or_download(file_path=filename, url=url)
            doc = pq(content)
            relegation_teams = []
            for team_id in range(self.get_number_teams()-4, self.get_number_teams()):
                relegation_teams.append(doc('.negro').eq(team_id).text().upper())

            return relegation_teams

    def get_current_journey(self):
        filename = os.path.join(self.SEASON_PATH, 'current_journey_calendar.html')
        url = BASE_URL + "resulcla.php"
        content = download(file_path=filename, url=url)
        doc = pq(content)
        prox_journey=doc('.estnegro')('td').eq(1).text()
        current_journey=(re.findall('\d+', prox_journey ))
        return int(current_journey[0])

    def get_next_journey(self):
        current_journey=self.get_current_journey()

        filename = os.path.join(self.SEASON_PATH, 'next_journey_calendar.html')
        url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(self.season_id, current_journey+1)
        content = download(file_path=filename, url=url)
        doc = pq(content)
        prox_journey=doc('.estnegro')('td').eq(1).text()
        current_journey=(re.findall('\d+', prox_journey ))
        return int(current_journey[0])

    def get_journey(self,journey):
        filename = os.path.join(self.SEASON_PATH, 'journey_{}_calendar.html').format(journey)
        url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(self.season_id, journey)
        content = download(file_path=filename, url=url)
        doc = pq(content)
        prox_journey = doc('.estnegro')('td').eq(1).text()
        current_journey = (re.findall('\d+', prox_journey))
        return int(current_journey[0])




