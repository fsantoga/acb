import os.path, re, datetime, difflib, logging
from pyquery import PyQuery as pq
from src.download import open_or_download, sanity_check, get_page
from src.season import BASE_URL
from models.basemodel import BaseModel
from models.team import Team, TeamName
from peewee import (PrimaryKeyField, TextField, IntegerField,
                    DateTimeField, ForeignKeyField, BooleanField)

class Event(BaseModel):
    id = PrimaryKeyField()
    eventid = IntegerField()
    gameid = IntegerField(index=True)
    teamid = TextField(null=True)
    legend = TextField(null=True)
    extra_info = TextField(null=True)
    elapsed_time = IntegerField(null=True)
    display_name = TextField(null=True)
    jersey = IntegerField(null=True)
    home_score = IntegerField(null=True)
    away_score = IntegerField(null=True)

    @staticmethod
    def save_events(season, logging_level=logging.INFO):
        """
        Method for saving locally the games of a season.

        :param season: int
        :param logging_level: logging object
        :return:
        """
        from_journey = 1
        to_journey = 50

        logging.basicConfig(level=logging_level)
        logger = logging.getLogger(__name__)

        logger.info('Taking all games-events...')

        fibalivestats_ids = {}
        for i in range(from_journey, to_journey + 1):
            url = "http://jv.acb.com/historico.php?jornada={}&cod_competicion=LACB&cod_edicion={}".format(i,season.season_id)
            content = get_page(url)

            fls_ids = re.findall(r'<div class="partido borde_azul" id="partido-([0-9]+)">', content, re.DOTALL)
            game_ids = re.findall(r'"http://www.acb.com/fichas/LACB([0-9]+).php', content, re.DOTALL)
            fibalivestats_ids.update(dict(zip(fls_ids, game_ids)))

        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info('Starting downloading...')

        for i, (fls_id, game_id) in enumerate(fibalivestats_ids.items()):
            eventURL="http://jv.acb.com/partido.php?c={}".format(fls_id)
            filename = os.path.join(season.EVENTS_PATH, str(game_id)+"-"+str(fls_id) + ".html")

            open_or_download(file_path=filename, url=eventURL)

            # Debugging
            if i % (round(len(fibalivestats_ids) / 3)) == 0:
                logger.info('{}% already downloaded'.format(round(float(i) / len(fibalivestats_ids) * 100)))

        logger.info('Downloading finished!)')

    @staticmethod
    def sanity_check(season, logging_level=logging.INFO):
        sanity_check(season.EVENTS_PATH, logging_level)