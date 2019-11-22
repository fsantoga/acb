import os.path
import re
import datetime
import glob
import logging
from pyquery import PyQuery as pq
from src.download import open_or_download, sanity_check, open_or_download_photo
from models.basemodel import BaseModel, db
from peewee import (PrimaryKeyField, TextField,
                    DoubleField, DateTimeField, BooleanField, ForeignKeyField, CharField, IntegerField)
from tools.exceptions import InvalidCallException
from variables import PLAYERS_PATH, COACHES_PATH
from tools.log import logger
from tools.checkpoint import Checkpoint
from collections import OrderedDict


class Actor(BaseModel):

    """
    Class representing an Actor.
    An actor can be either a player or a coach.
    """
    id = IntegerField(primary_key=True)
    is_coach = BooleanField(null=True)
    display_name = TextField(index=True, null=True)
    full_name = TextField(null=True)
    nationality = TextField(null=True)
    birth_place = TextField(null=True)
    birth_date = DateTimeField(null=True)
    position = TextField(null=True)
    height = DoubleField(null=True)
    license = TextField(null=True)
    twitter = TextField(null=True)
    instagram = TextField(null=True)

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
        players_ids = [p[0] for p in players]
        checkpoint = Checkpoint(length=len(players_ids), chunks=10, msg='players already downloaded')
        for player_id in players_ids:
            _download_player(player_id)
            next(checkpoint)
        logger.info(f"Downloaded {len(players_ids)} players!")

        # Download coaches
        coaches_ids = [c[0] for c in coaches]
        checkpoint = Checkpoint(length=len(coaches_ids), chunks=10, msg='coaches already downloaded')
        for coach_id in coaches_ids:
            _download_coach(coach_id)
            next(checkpoint)
        logger.info(f"Downloaded {len(coaches_ids)} coaches!")

    @staticmethod
    def create_instances(season):
        players, coaches = Actor.get_actors(season, unique=False)

        with db.atomic():
            # Insert coaches
            for coach_id, coach_name in coaches:
                Actor.insert_actor(actor_id=coach_id, is_coach=True)
                ActorName.create_instance(actor_id=coach_id, actor_name=coach_name)
            # Insert players
            for player_id, player_name in players:
                Actor.insert_actor(actor_id=player_id, is_coach=False)
                ActorName.create_instance(actor_id=player_id, actor_name=player_name)




            # try:
            #     if len(actors) and cont % (round(len(actors) / 3)) == 0:
            #         logger.info( '{}% already updated'.format(round(float(cont) / len(actors) * 100)))
            # except ZeroDivisionError:
            #     pass

    @staticmethod
    def insert_actor(actor_id, is_coach):
        actor, created = Actor.get_or_create(**{'id': actor_id, 'is_coach': is_coach})
        if not created:  # If the actor exists, we do not need to insert it
            return

        ACTORS_FOLDER = COACHES_PATH if is_coach else PLAYERS_PATH
        filename = os.path.join(ACTORS_FOLDER, actor_id + '.html')
        content = open_or_download(file_path=filename)

        if '<div class="cuerpo cuerpo_equipo">' not in content:
            logger.error(f"Ghost actor: {actor_id} is_coach: {is_coach}")
            return

        personal_info = actor._get_personal_info(content)
        twitter = actor._get_twitter(content)
        instagram = actor._get_instagram(content)

        actor._download_photo(content, ACTORS_FOLDER)

        if twitter:
            personal_info.update({'twitter': twitter})
        if instagram:
            personal_info.update({'instagram': instagram})

        # The update query requires to specify the id
        # Otherwise it updates the whole table.
        actor.update(**personal_info).where(Actor.id == actor.id).execute()

    @staticmethod
    def get_actors(season, unique=True):
        """
        Iterates over all the games and retrieve combinations of (actor_id, actor_name).
        If unique=True -> discards repeated actors (an actor can have several names across the season)

        :param season:
        :param: unique:
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

        # Elegant solution to remove duplicates
        # from https://www.geeksforgeeks.org/python-remove-tuples-having-duplicate-first-value-from-given-list-of-tuples/
        if unique:
            return OrderedDict(players_ids).items(), OrderedDict(coaches_ids).items()
        else:
            return players_ids, coaches_ids

    def _get_personal_info(self, content):
        doc = pq(content)

        full_name = doc("div[class='datos_secundarios roboto_condensed']")
        full_name = full_name("span").text()

        display_name = doc("h1[class='f-l-a-100 roboto_condensed_bold mayusculas']").text()

        if self.is_coach:
            birthday_html = "datos_basicos fecha_nacimiento roboto_condensed"
        else:
            birthday_html = "datos_secundarios fecha_nacimiento roboto_condensed"
        birthdate = doc(f"div[class='{birthday_html}']")
        birthdate = birthdate("span[class='roboto_condensed_bold']").eq(0).text()
        birthdate = birthdate.split()[0]
        day, month, year = re.search(r'([0-9]+)/([0-9]+)/([0-9]+)', birthdate).groups()
        birthdate = datetime.datetime(year=int(year), month=int(month), day=int(day))

        birthplace = doc("div[class='datos_secundarios lugar_nacimiento roboto_condensed']")
        birthplace = birthplace("span[class='roboto_condensed_bold']").eq(0).text()

        if birthplace.startswith(","): # example: , Reino Unido (for Abodunrin Gabriel Olaseni))
            birthplace = birthplace[2:]

        nationality = doc("div[class='datos_secundarios nacionalidad roboto_condensed']")
        nationality = nationality("span[class='roboto_condensed_bold']").text()

        if not self.is_coach:
            position = doc("div[class='datos_basicos posicion roboto_condensed']")
            position = position("span").text()

            height = doc("div[class='datos_basicos altura roboto_condensed']")
            height = height("span").text()
            height = height.split()[0]
            height = height.replace(",", "") # to centimeters

            # license is a reserved word in Python
            _license = doc("div[class='datos_secundarios licencia roboto_condensed']")
            _license = _license("span[class='roboto_condensed_bold']").text()

        personal_info = {
            'full_name': full_name,
            'display_name': display_name,
            'birth_date': birthdate,
            'birth_place': birthplace,
            'nationality': nationality,
        }

        if not self.is_coach:
            personal_info.update({
                'position': position,
                'height': height,
                'nationality': nationality,
                'license': _license,
            })

        return personal_info

    def _get_twitter(self, content):
        """
        Get the twitter of an actor, if it exists.
        :param raw_doc: String
        :return: twitter
        """
        # Regex to match everything except ACBCOM
        doc = pq(content)
        twitter = doc("article[class='redondo twitter']")
        if twitter:
            twitter = twitter("a").attr("href")
            return twitter
        return

    def _get_instagram(self, content):
        """
        Get the instagram of an actor, if it exists.
        :param raw_doc: String
        :return: twitter
        """
        doc = pq(content)
        instagram = doc("article[class='redondo instagram']")
        if instagram:
            instagram = instagram("a").attr("href")
            return instagram
        return

    def _download_photo(self, content, folder):
        doc = pq(content)
        photo_url = doc("div[class='foto']")
        photo_url = photo_url("img").attr("src")
        if photo_url == '/Images/Web/silueta2.gif':  # no photo
            return
        photo_filename = os.path.join(folder, 'photos', self.id + '.jpg')
        open_or_download_photo(file_path=photo_filename, url=photo_url)

    @staticmethod
    def sanity_check(logging_level=logging.INFO):
        from src.season import BASE_URL, PLAYERS_PATH, COACHES_PATH
        sanity_check(PLAYERS_PATH, logging_level)
        sanity_check(COACHES_PATH, logging_level)

    # @staticmethod
    # def update_content(logging_level=logging.INFO):
    #     """
    #     First we insert the instances in the database with basic information and later we update the rest of fields.
    #     We update the information of the actors that have not been filled yet in the database.
    #     """
    #     logging.basicConfig(level=logging_level)
    #     logger = logging.getLogger(__name__)
    #
    #     logger.info('Starting to update the actors that have not been filled yet...')
    #     actors = Actor.select().where(Actor.full_name >> None)
    #     for cont, actor in enumerate(actors):
    #         actor._update_content()
    #         try:
    #             if len(actors) and cont % (round(len(actors) / 3)) == 0:
    #                 logger.info( '{}% already updated'.format(round(float(cont) / len(actors) * 100)))
    #         except ZeroDivisionError:
    #             pass
    #
    #     logger.info('Update finished! ({} actors)\n'.format(len(actors)))
    #
    # def _update_content(self):
    #     from src.season import BASE_URL, PLAYERS_PATH, COACHES_PATH
    #     """
    #     Update the information of a particular actor.
    #     """
    #     logging.basicConfig(level=logging.INFO)
    #     logger = logging.getLogger(__name__)
    #
    #     folder = COACHES_PATH if self.is_coach else PLAYERS_PATH
    #     url_tag = 'entrenador' if self.is_coach else 'jugador'
    #
    #     filename = os.path.join(folder, self.actor_acbid + '.html')
    #     url = os.path.join(BASE_URL, '{}.php?id={}'.format(url_tag, self.actor_acbid))
    #     content = open_or_download(file_path=filename, url=url)
    #
    #     personal_info = self._get_personal_info(content)
    #     twitter = self._get_twitter(content)
    #     photo_url = self._get_photo(content)
    #
    #     photo_filename = os.path.join(folder, self.actor_acbid + '.jpg')
    #     try:
    #         urllib.request.urlretrieve(photo_url,photo_filename)
    #     except:
    #         logger.info('Error downloading image: {}'.format(photo_url))
    #
    #     personal_info.update({'twitter': twitter})
    #
    #     if personal_info is None:
    #         pass
    #     else:
    #         try:
    #             Actor.update(**personal_info).where((Actor.actor_acbid == self.actor_acbid) & (Actor.display_name == self.display_name)).execute()
    #         except Exception as e:
    #             print(e)
    #             pass

    # def _get_personal_info(self, raw_doc):
    #     """
    #     Get personal information about an actor
    #     :param raw_doc: String
    #     :return: dict with the info.
    #     """
    #     doc = pq(raw_doc)
    #     personal_info = dict()
    #     for cont, td in enumerate(doc('.titulojug').items()):
    #         header = list(map(lambda x: x.strip(), td.text().split("|"))) if "|" in td.text() else [td.text()]
    #         data = list(map(lambda x: x.strip(), doc('.datojug').eq(cont).text().split("|"))) if td.text() else [td.text()]
    #
    #         if header[0].startswith("nombre completo"):
    #             personal_info['full_name'] = data[0]
    #
    #         elif header[0].startswith("lugar y fecha"):
    #             try:
    #                 place, day, month, year = re.search(r'(.*), ([0-9]+)/([0-9]+)/([0-9]+)', data[0]).groups()
    #                 personal_info['birth_place'] = place.strip()
    #                 personal_info['birth_date'] = datetime.datetime(year=int(year), month=int(month), day=int(day))
    #             except:
    #                 logging.warning('The actor {} has an error in the birthdate and birthplace. Msg: {}'.format(personal_info['full_name'], data[0]))
    #                 personal_info['birth_place'] = None
    #                 personal_info['birth_date'] = None
    #                 pass
    #
    #         elif header[0].startswith('posic'):
    #             for i, field in enumerate(header):
    #                 if field.startswith('posic'):
    #                     personal_info['position'] = data[i]
    #                 elif field.startswith('altura'):
    #                     personal_info['height'] = data[i].split(" ")[0]
    #                 elif field.startswith('peso'):
    #                     personal_info['weight'] = data[i].split(" ")[0]
    #                 else:
    #                     logging.warning("Actor's field not found: {}".format(field))
    #                     return None
    #
    #         elif header[0].startswith('nacionalidad'):
    #             for i, field in enumerate(header):
    #                 if field.startswith('nacionalidad'):
    #                     personal_info['nationality'] = data[i]
    #                 elif field.startswith('licencia'):
    #                     personal_info['license'] = data[i]
    #                 else:
    #                     logging.warning("Actor's field not found: {}".format(field))
    #                     return None
    #
    #         elif header[0].startswith('debut en ACB'):
    #             try:
    #                 day, month, year = re.search(r'([0-9]+)/([0-9]+)/([0-9]+)', data[0]).groups()
    #                 personal_info['debut_acb'] = datetime.datetime(year=int(year), month=int(month), day=int(day))
    #             except:
    #                 logging.warning('The actor {} has an error in the debut_acb. Msg: {}'.format(personal_info['full_name'], data[0]))
    #                 return None
    #
    #         else:
    #             logging.error('A field of the personal information does not match our patterns: ''{} in {}'.format(td.text(), personal_info['full_name']))
    #             return None
    #
    #     return personal_info



    # def _get_photo(self, raw_doc):
    #     """
    #     Get the twitter of an actor, if it exists.
    #     :param raw_doc: String
    #     :return: twitter
    #     """
    #     doc = pq(raw_doc)
    #     photo_data = doc('#portadafoto')
    #     url=None
    #
    #     if photo_data('img'):
    #         photo=photo_data('img')
    #         url = photo.attr['src']
    #
    #     return url

class ActorName(BaseModel):
    """
        Class representing a ActorName.
    """
    id = PrimaryKeyField()
    actor_id = ForeignKeyField(Actor, related_name='names', index=True)
    name = CharField(max_length=255)

    class Meta:
        indexes = (
            (('actor_id', 'name'), True),
        )

    @staticmethod
    def create_instance(actor_id, actor_name):
        ActorName.get_or_create(**{'actor_id': actor_id, 'name': actor_name})