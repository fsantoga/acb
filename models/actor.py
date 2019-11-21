import os.path
import re
import datetime
import urllib.request
import glob
import logging
from pyquery import PyQuery as pq
from src.download import open_or_download, sanity_check
from models.basemodel import BaseModel
from peewee import (PrimaryKeyField, TextField,
                    DoubleField, DateTimeField, BooleanField)
from tools.exceptions import InvalidCallException
from variables import PLAYERS_PATH, COACHES_PATH
from tools.log import logger
from tools.checkpoint import Checkpoint


class Actor(BaseModel):

    """
    Class representing an Actor.
    An actor can be either a player or a coach.
    """
    id = PrimaryKeyField()
    actor_acbid = TextField(index=True)
    is_coach = BooleanField(null=True)
    display_name = TextField(index=True, null=True)
    full_name = TextField(null=True)
    nationality = TextField(null=True)
    birth_place = TextField(null=True)
    birth_date = DateTimeField(null=True)
    position = TextField(null=True)
    height = DoubleField(null=True)
    weight = DoubleField(null=True)
    license = TextField(null=True)
    debut_acb = DateTimeField(null=True)
    twitter = TextField(null=True)

    @staticmethod
    def download_actors(season):
        """
        Downloads the actors webpages for a season.
        :param season:
        :return:
        """
        def _download_player(player_id):
            """
            Downloads the player webpage.
            :param player_id:
            :return:
            """
            filename = os.path.join(PLAYERS_PATH, f"{player_id}.html")
            url = os.path.join(f"http://www.acb.com/jugador/temporada-a-temporada/id/{player_id}")
            logger.info(f"Retrieving player webpage from: {url}")
            open_or_download(file_path=filename, url=url)

        def _download_coach(coach_id):
            """
            Downloads the coach webpage.
            :param coach_id:
            :return:
            """
            filename = os.path.join(COACHES_PATH, f"{coach_id}.html")
            url = os.path.join(f"http://www.acb.com/entrenador/trayectoria-logros/id/{coach_id}")
            logger.info(f"Retrieving coach webpage from: {url}")
            open_or_download(file_path=filename, url=url)

        # Get the actors of the season
        players, coaches = Actor.get_actors(season)

        # Download players
        unique_players_ids = [p[0] for p in players]
        unique_players_ids = set(unique_players_ids)
        checkpoint = Checkpoint(length=len(unique_players_ids), chunks=10, msg='players already downloaded')
        for player_id in unique_players_ids:
            _download_player(player_id)
            next(checkpoint)

        # Download coaches
        unique_coaches_ids = [c[0] for c in coaches]
        unique_coaches_ids = set(unique_coaches_ids)
        checkpoint = Checkpoint(length=len(unique_coaches_ids), chunks=10, msg='coaches already downloaded')
        for coach_id in unique_coaches_ids:
            _download_coach(coach_id)
            next(checkpoint)

    @staticmethod
    def get_actors(season):
        """
        Iterates over all the games and retrieve unique combinations of (actor_id, actor_name).

        # TODO: Un mismo jugador puede tener varios nombres!!!
        # print(len(players))
        # unique_names = set()
        # unique_ids = set()
        # match = dict()
        # for p_id, p_name in players:
        #     if p_id in unique_ids:
        #         print(p_name, match[p_id])
        #     else:
        #         unique_ids.add(p_id)
        #         unique_names.add(p_name)
        #         match[p_id] = p_name
        # Vildoza, Luca Luca Vildoza
        # Smits, Rolands Rolands Smits

        :param season:
        :return:
        """
        def _get_all_actors(game):
            """
            Iterates over all the games and extract the players and coaches
            :param game:
            :return:
            """
            with open(game, 'r', encoding="utf8") as f:
                content = f.read()
            players = re.findall(
                r'<td class="nombre jugador ellipsis"><a href="/jugador/ver/([0-9]+)-.*?">(.*?)</a></td>',
                content, re.DOTALL)
            coaches = re.findall(r'<td class="nombre entrenador"><a href="/entrenador/ver/([0-9]+)-.*?">(.*?)</a></td>',
                                 content, re.DOTALL)
            return players, coaches

        players_ids = set()
        coaches_ids = set()
        games_files = glob.glob(f"{season.GAMES_PATH}/*.html")
        if len(games_files) == 0:
            raise InvalidCallException(message='season.download_games() must be called first')

        for game in games_files:
            players, coaches = _get_all_actors(game)
            players_ids.update(players)
            coaches_ids.update(coaches)
        return players_ids, coaches_ids











    # def save_actors(logging_level=logging.INFO):
    #     """
    #     Method for saving locally the actors.
    #     :param logging_level: logging object
    #     """
    #     logging.basicConfig(level=logging_level)
    #     logger = logging.getLogger(__name__)
    #
    #     logger.info('Starting the download of actors...')
    #     actors = Actor.select()
    #     for cont, actor in enumerate(actors):
    #         folder = COACHES_PATH if actor.is_coach else PLAYERS_PATH
    #         url_tag = 'entrenador' if actor.is_coach else 'jugador'
    #
    #         filename = os.path.join(folder, actor.actor_acbid + '.html')
    #         url = os.path.join(BASE_URL, '{}.php?id={}'.format(url_tag, actor.actor_acbid))
    #         open_or_download(file_path=filename, url=url)
    #
    #         if cont % (round(len(actors) / 3)) == 0:
    #             logger.info('{}% already downloaded'.format(round(float(cont) / len(actors) * 100)))
    #
    #     logger.info('Downloading finished!\n')

    @staticmethod
    def sanity_check(logging_level=logging.INFO):
        from src.season import BASE_URL, PLAYERS_PATH, COACHES_PATH
        sanity_check(PLAYERS_PATH, logging_level)
        sanity_check(COACHES_PATH, logging_level)

    @staticmethod
    def update_content(logging_level=logging.INFO):
        """
        First we insert the instances in the database with basic information and later we update the rest of fields.
        We update the information of the actors that have not been filled yet in the database.
        """
        logging.basicConfig(level=logging_level)
        logger = logging.getLogger(__name__)

        logger.info('Starting to update the actors that have not been filled yet...')
        actors = Actor.select().where(Actor.full_name >> None)
        for cont, actor in enumerate(actors):
            actor._update_content()
            try:
                if len(actors) and cont % (round(len(actors) / 3)) == 0:
                    logger.info( '{}% already updated'.format(round(float(cont) / len(actors) * 100)))
            except ZeroDivisionError:
                pass

        logger.info('Update finished! ({} actors)\n'.format(len(actors)))

    def _update_content(self):
        from src.season import BASE_URL, PLAYERS_PATH, COACHES_PATH
        """
        Update the information of a particular actor.
        """
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        folder = COACHES_PATH if self.is_coach else PLAYERS_PATH
        url_tag = 'entrenador' if self.is_coach else 'jugador'

        filename = os.path.join(folder, self.actor_acbid + '.html')
        url = os.path.join(BASE_URL, '{}.php?id={}'.format(url_tag, self.actor_acbid))
        content = open_or_download(file_path=filename, url=url)

        personal_info = self._get_personal_info(content)
        twitter = self._get_twitter(content)
        photo_url = self._get_photo(content)

        photo_filename = os.path.join(folder, self.actor_acbid + '.jpg')
        try:
            urllib.request.urlretrieve(photo_url,photo_filename)
        except:
            logger.info('Error downloading image: {}'.format(photo_url))

        personal_info.update({'twitter': twitter})

        if personal_info is None:
            pass
        else:
            try:
                Actor.update(**personal_info).where((Actor.actor_acbid == self.actor_acbid) & (Actor.display_name == self.display_name)).execute()
            except Exception as e:
                print(e)
                pass

    def _get_personal_info(self, raw_doc):
        """
        Get personal information about an actor
        :param raw_doc: String
        :return: dict with the info.
        """
        doc = pq(raw_doc)
        personal_info = dict()
        for cont, td in enumerate(doc('.titulojug').items()):
            header = list(map(lambda x: x.strip(), td.text().split("|"))) if "|" in td.text() else [td.text()]
            data = list(map(lambda x: x.strip(), doc('.datojug').eq(cont).text().split("|"))) if td.text() else [td.text()]

            if header[0].startswith("nombre completo"):
                personal_info['full_name'] = data[0]

            elif header[0].startswith("lugar y fecha"):
                try:
                    place, day, month, year = re.search(r'(.*), ([0-9]+)/([0-9]+)/([0-9]+)', data[0]).groups()
                    personal_info['birth_place'] = place.strip()
                    personal_info['birth_date'] = datetime.datetime(year=int(year), month=int(month), day=int(day))
                except:
                    logging.warning('The actor {} has an error in the birthdate and birthplace. Msg: {}'.format(personal_info['full_name'], data[0]))
                    personal_info['birth_place'] = None
                    personal_info['birth_date'] = None
                    pass

            elif header[0].startswith('posic'):
                for i, field in enumerate(header):
                    if field.startswith('posic'):
                        personal_info['position'] = data[i]
                    elif field.startswith('altura'):
                        personal_info['height'] = data[i].split(" ")[0]
                    elif field.startswith('peso'):
                        personal_info['weight'] = data[i].split(" ")[0]
                    else:
                        logging.warning("Actor's field not found: {}".format(field))
                        return None

            elif header[0].startswith('nacionalidad'):
                for i, field in enumerate(header):
                    if field.startswith('nacionalidad'):
                        personal_info['nationality'] = data[i]
                    elif field.startswith('licencia'):
                        personal_info['license'] = data[i]
                    else:
                        logging.warning("Actor's field not found: {}".format(field))
                        return None

            elif header[0].startswith('debut en ACB'):
                try:
                    day, month, year = re.search(r'([0-9]+)/([0-9]+)/([0-9]+)', data[0]).groups()
                    personal_info['debut_acb'] = datetime.datetime(year=int(year), month=int(month), day=int(day))
                except:
                    logging.warning('The actor {} has an error in the debut_acb. Msg: {}'.format(personal_info['full_name'], data[0]))
                    return None

            else:
                logging.error('A field of the personal information does not match our patterns: ''{} in {}'.format(td.text(), personal_info['full_name']))
                return None

        return personal_info

    def _get_twitter(self, raw_doc):
        """
        Get the twitter of an actor, if it exists.
        :param raw_doc: String
        :return: twitter
        """
        twitter = re.search(r'"http://www.twitter.com/(.*?)"', raw_doc)
        try:
            twitter = twitter.groups()[0]
            if twitter=="ACBCOM":
                twitter = None
                return twitter
            else:
                return twitter.groups()[0] if twitter else None
        except:
            pass

    def _get_photo(self, raw_doc):
        """
        Get the twitter of an actor, if it exists.
        :param raw_doc: String
        :return: twitter
        """
        doc = pq(raw_doc)
        photo_data = doc('#portadafoto')
        url=None

        if photo_data('img'):
            photo=photo_data('img')
            url = photo.attr['src']

        return url
