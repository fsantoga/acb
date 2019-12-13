from tools.log import logger
from models.game import Game
from models.team import Team
from models.participant import Participant
from models.actor import Actor
from models.event import Event
from variables import *
from tools.lengua import get_playoff_games
import datetime


from_journey = 1
to_journey = 54

# TODO, hacer lingual mas generico y que cubra este caso
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
    def __init__(self, season, competition='Liga'):
        logger.info(f"Creating Season: {season}")

        self.season = season
        self.season_id = season - FIRST_SEASON + 1  # First season in 1956 noted as 1.
        self.current_journey = None
        self.competition = competition
        self.SEASON_PATH = os.path.join(DATA_PATH, str(self.season))
        self.GAMES_PATH = os.path.join(self.SEASON_PATH, 'games')
        self.JOURNEYS_PATH = os.path.join(self.GAMES_PATH, 'journeys')
        self.TEAMS_PATH = os.path.join(self.SEASON_PATH, 'teams')

        validate_dir(self.SEASON_PATH)
        validate_dir(self.GAMES_PATH)
        validate_dir(self.JOURNEYS_PATH)
        validate_dir(self.TEAMS_PATH)

        if self.season >= 2016:
            self.EVENTS_PATH = os.path.join(self.SEASON_PATH, 'events')
            self.SHOTCHART_PATH = os.path.join(self.SEASON_PATH, 'shotchart')

            validate_dir(self.EVENTS_PATH)
            validate_dir(os.path.join(self.EVENTS_PATH, 'journeys'))
            validate_dir(self.SHOTCHART_PATH)

        #self.current_journey=self.get_current_journey(season)
        # self.relegation_playoff_seasons = [1994, 1995, 1996, 1997]

        # Get the teams of the season
        self.teams = None
        # self.num_teams = len(self.teams)
        # self.playoff_format = self.get_playoff_format()
        # self.mismatched_teams = []

        #self.game_events_ids=self.get_game_events_ids()
        #self.game_ids=self.get_game_ids()

        #if self.season == get_current_season():
        #    self.current_game_events_ids=self.get_current_game_events_ids()

    def download_games(self):
        """
        Downloads the game of a season.
        :return:
        """
        Game.download(self)

    def download_teams(self):
        """
        Downloads the teams of a season.
        :return:
        """
        Team.download_teams(self)

    def download_actors(self):
        """
        Downloads the actors (players and coaches) of a season
        :return:
        """
        Actor.download_actors(self)

    def download_events(self):
        Event.download(self)

    def populate_teams(self):
        """
        Populates the Team and TeamName tables for a season
        :return:
        """
        Team.create_instances(self)

    def populate_actors(self):
        """
        Populates the Actor table for a season
        :return:
        """
        Actor.create_instances(self)

    def populate_games(self):
        """
        Populates the Game table for a season
        :return:
        """
        Game.create_instances(self)

    def populate_participants(self):
        """
        Populates the Participant table for a season
        :return:
        """
        Participant.create_instances(self)

    def populate_events(self):
        """
        Populates the Event table for a season
        :return:
        """
        Event.create_instances(self)

    #
    #
    # def get_game_events_ids(self):
    #     game_events_ids = {}
    #     for i in range(from_journey, to_journey + 1):
    #         url = "http://jv.acb.com/historico.php?jornada={}&cod_competicion=LACB&cod_edicion={}".format(i,self.season_id)
    #         content = get_page(url)
    #
    #         fls_ids = re.findall(r'<div class="partido borde_azul" id="partido-([0-9]+)">', content, re.DOTALL)
    #         game_ids = re.findall(r'"http://www.acb.com/fichas/LACB([0-9]+).php', content, re.DOTALL)
    #         game_events_ids.update(dict(zip(fls_ids, game_ids)))
    #
    #     return game_events_ids
    #
    # def get_current_game_events_ids(self):
    #     current_game_events_ids = {}
    #     for i in range(from_journey, self.get_current_journey() + 1):
    #         url = "http://jv.acb.com/historico.php?jornada={}&cod_competicion=LACB&cod_edicion={}".format(i,self.season_id)
    #         content = get_page(url)
    #
    #         fls_ids = re.findall(r'<div class="partido borde_azul" id="partido-([0-9]+)">', content, re.DOTALL)
    #         game_ids = re.findall(r'"http://www.acb.com/fichas/LACB([0-9]+).php', content, re.DOTALL)
    #         current_game_events_ids.update(dict(zip(fls_ids, game_ids)))
    #
    #     return current_game_events_ids
    #
    #
    # def get_playoff_format(self):
    #     """
    #     Gets the playoff format of the season.
    #
    #     TODO: now we do not have access to the playoff webpage, this method might fail in other cases...
    #     TODO: e.g: get_number_games_playoff()
    #
    #     Source:
    #     - https://web.archive.org/web/20190403020219/http://www.acb.com/playoff.php?cod_competicion=LACB&cod_edicion=62
    #     - For 1994 and 1995: page 32 in http://www.acb.com/publicaciones/guia1995
    #     """
    #     logger.info(f"The playoff format is {PLAYOFF_MAPPER[self.season]}")
    #     return PLAYOFF_MAPPER[self.season]

    # def get_teams_ids(self):
    #     # TODO: temporary solution
    #     return list(self.teams.keys())

    @property
    def playoff_games_to_phase_mapper(self):
        # todo: comment
        return get_playoff_games(self)

    def get_number_games_regular_season(self):
        # todo: comment
        if not self.teams:
            self.teams = Team.get_teams(self)
        return (len(self.teams) - 1) * len(self.teams)

    def is_current_season(self):
        # TODO: comment
        # We take te current time
        now = datetime.datetime.now()

        # We extract the current year and the current month
        current_year = now.year
        current_month = now.month

        # We check if the current_month is between January and July. We need to know the real year of the current season
        if 1 <= current_month < 8:
            current_year = current_year - 1

        return current_year == self.season

    # def get_number_games_playoff(self):
    #     games_per_round = [4, 2, 1]  # Quarter-finals, semifinals, final.
    #     try:
    #         return sum(np.array(self.playoff_format) * np.array(games_per_round))  # Element-wise multiplication.
    #     except Exception as e:
    #         logger.info('No se ha jugado ningun partido de playoff...\n')
    #         #print(e)
    #         return 0
    #
    # def get_number_games(self):
    #     return self.get_number_games_regular_season() \
    #            + self.get_number_games_playoff() \
    #            + self.get_number_games_relegation_playoff()
    #
    # def get_number_games_relegation_playoff(self):
    #     return 5*2 if self.season in self.relegation_playoff_seasons else 0
    #
    # def get_relegation_teams(self):
    #     relegation_teams = {
    #         # de aqui para atras incluso mas complicado...
    #         1992: [48, 26, 12, 40], # Club Basket Ferrys Lliria, Caceres CB, CB Juver Murcia,  Argal Huesca
    #         1993: [71, 12, 32, 40], # Fórum Valladolid, CB Murcia, Valvi Girona, Argal Huesca
    #         1994: [13, 40, 32, 25], # Pamesa Valencia, Somontano Huesca, Valvi Girona, Breogán Lugo
    #         1995: [58, 31, 22, 40], # Amway Zaragoza, Estudiantes Argentaria, Festina Andorra, Grupo AGB Huesca
    #         1996: [71, 17, 58, 12], # Fórum Valladolid, Baloncesto Fuenlabrada, Xacobeo 99 Ourense, CB Murcia Artel
    #         1997: [38,  1, 58, 26], # CB Ciudad De Huelva, Covirán Sierra Nevada Granada, Ourense Xacobeo 99, Caceres CB
    #         # 1997-1998 fue la ultima temporada con esto
    #     }
        # if self.season <= 1994:
        #     return {1994: }[self.season]
        # else:
        #     filename = os.path.join(self.SEASON_PATH, 'relegation_playoff.html')
        #     url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(self.season_id, (self.num_teams-1)*2)
        #     content = open_or_download(file_path=filename, url=url)
        #     doc = pq(content)
        #     relegation_teams = []
        #     for team_id in range(self.num_teams-4, self.num_teams):
        #         relegation_teams.append(doc('.negro').eq(team_id).text().upper())
        #
        #     return relegation_teams

    # def get_current_journey(self):
    #     filename = os.path.join(self.SEASON_PATH, 'current_journey_calendar.html')
    #     url = BASE_URL + "resulcla.php"
    #     content = download(file_path=filename, url=url)
    #     doc = pq(content)
    #     prox_journey=doc('.estnegro')('td').eq(1).text()
    #     current_journey=(re.findall('\d+', prox_journey ))
    #     return int(current_journey[0])
    #
    # def get_next_journey(self):
    #     current_journey=self.get_current_journey()
    #
    #     filename = os.path.join(self.SEASON_PATH, 'next_journey_calendar.html')
    #     url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(self.season_id, current_journey+1)
    #     content = download(file_path=filename, url=url)
    #     doc = pq(content)
    #     prox_journey=doc('.estnegro')('td').eq(1).text()
    #     current_journey=(re.findall('\d+', prox_journey ))
    #     return int(current_journey[0])

    # def get_journey(self, journey):
    #     filename = os.path.join(self.SEASON_PATH, 'journey_{}_calendar.html').format(journey)
    #     url = BASE_URL + "resulcla.php?codigo=LACB-{}&jornada={}".format(self.season_id, journey)
    #     content = download(file_path=filename, url=url)
    #     doc = pq(content)
    #     prox_journey = doc('.estnegro')('td').eq(1).text()
    #     current_journey = (re.findall('\d+', prox_journey))
    #     return int(current_journey[0])

s = Season(2018)
# s.download_teams()
# s.download_games() # TODO, participants and events dependen de esta ejecucion
# s.download_actors()
# s.download_events()
# s.populate_teams()
# s.populate_games()
# s.populate_actors()
s.populate_participants()
s.populate_events()


