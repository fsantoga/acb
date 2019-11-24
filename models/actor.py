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
from variables import PLAYERS_PATH, COACHES_PATH, REFEREES_PATH
from tools.log import logger
from tools.checkpoint import Checkpoint
from collections import OrderedDict
from tools.exceptions import DuplicatedActorId
from fuzzywuzzy import process
from fuzzywuzzy import fuzz

ACTORS_FOLDER_MAPPER = {
    'player': PLAYERS_PATH,
    'coach': COACHES_PATH,
    'referee': REFEREES_PATH,
}

class Actor(BaseModel):

    """
    Class representing an Actor.
    An actor can be a `player`, `coach` or `referee`.
    """
    id = IntegerField(primary_key=True)
    category = TextField(null=True)
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

        def _download_referee(referee_id):
            """
            Downloads the referee webpage.
            :param referee_id:
            :return:
            """
            filename = os.path.join(REFEREES_PATH, f"{referee_id}.html")
            url = os.path.join(f"http://www.acb.com/arbitro/hitos-logros/id/{referee_id}")
            logger.info(f"Retrieving referee webpage from: {url}")
            open_or_download(file_path=filename, url=url)

        # Get the actors of the season
        players, coaches, referees = Actor.get_actors(season)

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

        referees_ids = [r[0] for r in referees]
        checkpoint = Checkpoint(length=len(referees_ids), chunks=10, msg='coaches already downloaded')
        for referee_id in referees_ids:
            _download_referee(referee_id)
            next(checkpoint)
        logger.info(f"Downloaded {len(coaches_ids)} referees!")


    @staticmethod
    def create_instances(season):
        """
        Inserts all the actors and actornames of a season to the database.

        :param season:
        :return:
        """
        players, coaches, referees = Actor.get_actors(season, unique=False)

        with db.atomic():
            # Insert referees
            for referee_id, referee_name in referees:
                assert referee_id != 0
                Actor.create_instance(actor_id=referee_id, category='referee')
                ActorName.create_instance(actor_id=referee_id, actor_name=referee_name)

            # Insert coaches
            for coach_id, coach_name in coaches:
                assert coach_id != 0
                Actor.create_instance(actor_id=coach_id, category='coach')
                ActorName.create_instance(actor_id=coach_id, actor_name=coach_name)

            # Insert players
            for player_id, player_name in players:
                assert player_id != 0
                Actor.create_instance(actor_id=player_id, category='player')
                ActorName.create_instance(actor_id=player_id, actor_name=player_name)

    @staticmethod
    def create_instance(actor_id, category):
        """
        Creates an Actor instance.
        The category could be: `player`, `coach` or `referee`

        :param actor_id:
        :param category:
        :return:
        """
        actor, created = Actor.get_or_create(**{'id': actor_id, 'category': category})
        if not created:  # If the actor exists, we do not need to insert it
            return

        filename = os.path.join(ACTORS_FOLDER_MAPPER[category], actor_id + '.html')
        content = open_or_download(file_path=filename)

        if '<div class="cuerpo cuerpo_equipo">' not in content:
            logger.error(f"Ghost actor: {actor_id} category: {category}")
            return

        personal_info = actor._get_personal_info(content)
        twitter = actor._get_twitter(content)
        instagram = actor._get_instagram(content)
        actor._download_photo(content, ACTORS_FOLDER_MAPPER[category])

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
            referees = re.findall(r'<a href="/arbitro/ver/id/([0-9]+)">(.*?)</a>', content, re.DOTALL)
            return players, coaches, referees

        def fix_referees(referees):
            """
            Fix the missing ids of the referees of the season.

            Sometimes there are referees with id=0. So far, we've seen this when the name of the referee
            is in contracted form:
            - ('0', 'Aliaga, Jordi')
            Its equivalent match is -so far- in the list of referees:
            - ('20500228', 'Jordi Aliaga Sole')

            The approach to solve this problem is to do fuzzy search.

            :param referees:
            :return:
            """
            correct_referees = dict()
            invalid_referees = set()

            # Distinguish referees with id=0 (invalid_referees) and referees with ids (correct_referees)
            for referee_id, referee_name in referees:
                if referee_id != '0':
                    if referee_name in correct_referees and correct_referees[referee_name] != referee_id:
                        raise DuplicatedActorId(f"{referee_name}, {correct_referees[referee_name]}, {referee_id}")
                    correct_referees[referee_name] = referee_id
                else:
                    invalid_referees.add(referee_name)

            # Do fuzzy search for each invalid referee
            invalid_referees = list(invalid_referees)
            correct_referees_names = list(correct_referees.keys())
            for referee in invalid_referees:
                most_likely_coincide, threshold = process.extractOne(referee, correct_referees_names, scorer=fuzz.token_set_ratio)
                logger.warning(f"referee {referee} was match to {most_likely_coincide} with threshold {threshold}")
                assert threshold > 75, f"the threshold is too low for {referee} and match: {most_likely_coincide}"
                correct_referees[referee] = correct_referees[most_likely_coincide]

            # Convert back to set
            correct_referees = [(v, k) for k, v in correct_referees.items()]
            return correct_referees

        players_ids = set()
        coaches_ids = set()
        referees_ids = set()
        games_files = glob.glob(f"{season.GAMES_PATH}/*.html")
        if len(games_files) == 0:
            raise InvalidCallException(message='season.download_games() must be called first')

        for game in games_files:
            players, coaches, referees = _get_all_actors(game)
            players_ids.update(players)
            coaches_ids.update(coaches)
            referees_ids.update(referees)

        # Fix the referees
        referees_ids = fix_referees(referees_ids)

        # Elegant solution to remove duplicates
        # from https://www.geeksforgeeks.org/python-remove-tuples-having-duplicate-first-value-from-given-list-of-tuples/
        if unique:
            return OrderedDict(players_ids).items(), OrderedDict(coaches_ids).items(), OrderedDict(referees_ids).items()
        else:
            return players_ids, coaches_ids, referees_ids

    def _get_personal_info(self, content):
        """
        Extracts the personal information of an actor.

        :param content:
        :return:
        """
        doc = pq(content)

        display_name = doc("h1[class='f-l-a-100 roboto_condensed_bold mayusculas']").text()

        if self.category == 'player':
            birthday_html = "datos_secundarios fecha_nacimiento roboto_condensed"
        else:
            birthday_html = "datos_basicos fecha_nacimiento roboto_condensed"

        birthdate = doc(f"div[class='{birthday_html}']")
        birthdate = birthdate("span[class='roboto_condensed_bold']").eq(0).text()
        birthdate = birthdate.split()[0]
        day, month, year = re.search(r'([0-9]+)/([0-9]+)/([0-9]+)', birthdate).groups()
        birthdate = datetime.datetime(year=int(year), month=int(month), day=int(day))

        birthplace = doc("div[class='datos_secundarios lugar_nacimiento roboto_condensed']")
        birthplace = birthplace("span[class='roboto_condensed_bold']").eq(0).text()

        if birthplace.startswith(","): # example: , Reino Unido (for Abodunrin Gabriel Olaseni))
            birthplace = birthplace[2:]

        if self.category == 'referee':
            return {
                 'display_name': display_name,
                 'birth_date': birthdate,
                 'birth_place': birthplace,
                }

        full_name = doc("div[class='datos_secundarios roboto_condensed']")
        full_name = full_name("span").text()

        nationality = doc("div[class='datos_secundarios nacionalidad roboto_condensed']")
        nationality = nationality("span[class='roboto_condensed_bold']").text()

        if self.category == 'coach':
            return {
                'full_name': full_name,
                'display_name': display_name,
                'birth_date': birthdate,
                'birth_place': birthplace,
                'nationality': nationality,
                }

        # Only player data
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
            'position': position,
            'height': height,
            'license': _license,
        }
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
        :param content: String
        :return: twitter
        """
        doc = pq(content)
        instagram = doc("article[class='redondo instagram']")
        if instagram:
            instagram = instagram("a").attr("href")
            return instagram
        return

    def _download_photo(self, content, folder):
        """
        Downloads the photo of a player.
        :param content:
        :param folder:
        :return:
        """
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
        """
        Creates an ActorName object.

        :param actor_id:
        :param actor_name:
        :return:
        """
        ActorName.get_or_create(**{'actor_id': actor_id, 'name': actor_name})
