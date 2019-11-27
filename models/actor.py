import os.path
import re
import datetime
import glob
import logging
from pyquery import PyQuery as pq
from collections import defaultdict
from src.download import open_or_download, sanity_check, open_or_download_photo
from src.utils import cast_duples, flatten
from models.basemodel import BaseModel, db
from peewee import (PrimaryKeyField, TextField,
                    DoubleField, DateTimeField, CompositeKey, ForeignKeyField, CharField, IntegerField)
from tools.exceptions import InvalidCallException
from models.game import Game
from variables import PLAYERS_PATH, COACHES_PATH, REFEREES_PATH
from models.team import Team
from tools.log import logger
from tools.checkpoint import Checkpoint
from collections import OrderedDict
from tools.exceptions import DuplicatedActorId, MissingActorName
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
            for team_id, team_referees in referees.items():  # in this case team_id=0 for referees
                for referee_id, referee_name in team_referees:
                    assert referee_id != 0, (referee_id, referee_name)
                    Actor.create_instance(actor_id=referee_id, category='referee')
                    if referee_name != '':  # sometimes you have the id but not the name
                        ActorName.create_instance(actor_id=referee_id, team_id=team_id, season=season.season, actor_name=referee_name)

            # Insert coaches
            for team_id, team_coaches in coaches.items():
                for coach_id, coach_name in team_coaches:
                    assert coach_id != 0, (coach_id, coach_name)
                    Actor.create_instance(actor_id=coach_id, category='coach')
                    if coach_name != '':
                        ActorName.create_instance(actor_id=coach_id, team_id=team_id, season=season.season, actor_name=coach_name)

            # Insert players
            for team_id, team_players in players.items():
                for player_id, player_name in team_players:
                    assert player_id != 0, (player_id, player_name)
                    Actor.create_instance(actor_id=player_id, category='player')
                    if player_name != '':
                        ActorName.create_instance(actor_id=player_id, team_id=team_id, season=season.season, actor_name=player_name)

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

        filename = os.path.join(ACTORS_FOLDER_MAPPER[category], str(actor_id) + '.html')
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
        def _get_actors_from_game(game, is_home):
            with open(game, 'r', encoding="utf8") as f:
                content = f.read()
            doc = pq(content)
            tag = 'partido' if is_home else 'partido visitante'
            doc = doc(f"section[class='{tag}']")
            players = []
            players_doc = doc("td[class='nombre jugador ellipsis']")
            for player in players_doc.items():
                p_name = player('a').text()
                p_id = player('a').attr('href')
                if p_name == '' and p_id is None:
                    continue

                p_id = re.search('([0-9]+)', p_id)
                if p_id:
                    p_id = p_id.group(1)
                else:
                    p_id = 0
                players.append((p_id, p_name))

            coaches = []
            coaches_doc = doc("td[class='nombre entrenador']")
            for coach in coaches_doc.items():
                p_name = coach('a').text()
                p_id = coach('a').attr('href')
                if p_name == '' and p_id is None:
                    continue

                p_id = re.search('([0-9]+)', p_id)
                if p_id:
                    p_id = p_id.group(1)
                else:
                    p_id = 0
                coaches.append((p_id, p_name))

            # Get the referees from the content, not from the team
            referees = re.findall(r'<a href="/arbitro/ver/id/([0-9]+)">(.*?)</a>', content, re.DOTALL)
            players = cast_duples(players)
            coaches = cast_duples(coaches)
            referees = cast_duples(referees)
            return players, coaches, referees

        def _get_actors_from_team(team_file):
            with open(team_file, 'r', encoding="utf8") as f:
                content = f.read()
            doc = pq(content)
            players = []
            players_doc = doc("div[class='grid_plantilla principal']")
            players_doc = players_doc("div[class='foto']")
            for player in players_doc.items():
                p_id = player('a').attr('href')
                p_id = re.search(r'([0-9]+)', p_id).group(1)
                p_name = player('a').attr('title')
                players.append((p_id, p_name))

            # Categorias inferiores
            players_doc = doc("div[class='grid_plantilla']")
            players_doc = players_doc("div[class='foto']")
            for player in players_doc.items():
                p_id = player('a').attr('href')
                p_id = re.search(r'([0-9]+)', p_id).group(1)
                p_name = player('a').attr('title')
                players.append((p_id, p_name))

            # Dados de baja
            players_doc = doc("td[class='jugador primero']")
            for player in players_doc.items():
                p_id = player('a').attr('href')
                p_id = re.search(r'/jugador/ver/([0-9]+)', p_id)
                if not p_id:  # mixed players and coaches
                    continue
                p_id = p_id.group(1)
                p_name = player('span').text()
                players.append((p_id, p_name))

            # Coaches
            coaches = []
            coaches_doc = doc("div[class='grid_plantilla mb20']")
            coaches_doc = coaches_doc("div[class='foto']")
            for coach in coaches_doc.items():
                p_id = coach('a').attr('href')
                p_id = re.search(r'([0-9]+)', p_id).group(1)
                p_name = coach('a').attr('title')
                coaches.append((p_id, p_name))

            # Dados de baja
            coaches_doc = doc("td[class='jugador primero']")
            for coach in coaches_doc.items():
                p_id = coach('a').attr('href')
                p_id = re.search('/entrenador/ver/([0-9]+)', p_id)
                if not p_id:  # mixed players and coaches
                    continue
                p_id = p_id.group(1)
                p_name = coach('span')
                coaches.append((p_id, p_name))

            print(team_file, players)
            players = cast_duples(players)
            coaches = cast_duples(coaches)
            return players, coaches

        def fix_actors(actors, category):
            """
            Fix the missing ids of the actors of the season.

            Sometimes there are referees with id=0. So far, we've seen this when the name of the actor
            is in contracted form:
            - ('0', 'Aliaga, Jordi')
            Its equivalent match is -so far- in the list of referees:
            - ('20500228', 'Jordi Aliaga Sole')

            The approach to solve this problem is to do fuzzy search.

            :param actors:
            :return:
            """
            fixed_actors = dict()
            for team_id, team_actors in actors.items():
                correct_actors = dict()
                invalid_actors = set()

                # Distinguish actors with id=0 (invalid_actors) and actors with ids (correct_actors)
                for actor_id, actor_name in team_actors:
                    if actor_id != 0:
                        # Case when missing name but already inside
                        if actor_name == '':
                            if any(a_id == actor_id and a_name != '' for a_id, a_name in team_actors):
                                continue
                            else:
                                raise MissingActorName(f"{actor_id} team {team_id} and category {category}")

                        # Case duplicated actors
                        if actor_name in correct_actors and correct_actors[actor_name] != actor_id:  # duplicated
                            raise DuplicatedActorId(f"{actor_name}, {correct_actors[actor_name]}, {actor_id}, team: {team_id} and category {category}")
                        else:
                            correct_actors[actor_name] = actor_id
                    else:
                        invalid_actors.add(actor_name)

                # Do fuzzy search for each invalid referee
                invalid_actors = list(invalid_actors)
                correct_actors_names = list(correct_actors.keys())

                # Check if the actor name exists in database for that team
                for actor_name in invalid_actors:
                    try:
                        actor = ActorName.get(name=actor_name, team_id=team_id)
                        correct_actors[actor_name] = actor.actor_id
                        invalid_actors.remove(actor_name)
                    except ActorName.DoesNotExist:
                        pass

                # Otherwise, do fuzzy search between the actors of the team
                for actor_name in invalid_actors:
                    most_likely_coincide, threshold = process.extractOne(actor_name, correct_actors_names, scorer=fuzz.token_set_ratio)
                    logger.warning(f"actor {actor_name} was match to {most_likely_coincide} with threshold {threshold}")
                    assert threshold > 75, f"the threshold is too low for {actor_name} and match: {most_likely_coincide} {team_id} {team_actors}"
                    correct_actors[actor_name] = correct_actors[most_likely_coincide]

                # Convert back to set
                correct_actors = [(v, k) for k, v in correct_actors.items()]
                fixed_actors[team_id] = correct_actors
            return fixed_actors

        players_ids = defaultdict(set)
        coaches_ids = defaultdict(set)
        referees_ids = defaultdict(set)
        games_files = glob.glob(f"{season.GAMES_PATH}/*.html")
        teams_files = glob.glob(f"{season.TEAMS_PATH}/*-roster.html")
        if len(games_files) == 0:
            raise InvalidCallException(message='season.download_games() must be called first')
        if len(teams_files) == 0:
            raise InvalidCallException(message='season.download_teams() must be called first')

        # Get actors from games
        for game in games_files:
            home_team, away_team = Game.get_teams(game)
            home_players, home_coaches, referees = _get_actors_from_game(game, is_home=True)
            away_players, away_coaches, _ = _get_actors_from_game(game, is_home=False)
            players_ids[home_team].update(home_players)
            coaches_ids[home_team].update(home_coaches)
            players_ids[away_team].update(away_players)
            coaches_ids[away_team].update(away_coaches)
            referees_ids[0].update(referees)

        print(players_ids['9'])

        # Get actors from rosters (team)
        for team in teams_files:
            team_id = re.search(r'([0-9]+)-roster.html', team).group(1)

            players, coaches = _get_actors_from_team(team_file=team)
            players_ids[team_id].update(players)
            coaches_ids[team_id].update(coaches)
            if team_id == '9':
                print(players)

        print(players_ids['9'])

        # Fix the referees
        players_ids = fix_actors(players_ids, category='player')
        coaches_ids = fix_actors(coaches_ids, category='coach')
        referees_ids = fix_actors(referees_ids, category='referee')

        # Elegant solution to remove duplicates
        # from https://www.geeksforgeeks.org/python-remove-tuples-having-duplicate-first-value-from-given-list-of-tuples/
        if unique:
            players_ids = flatten(players_ids.values())
            coaches_ids = flatten(coaches_ids.values())
            referees_ids = flatten(referees_ids.values())
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
        if not photo_url or photo_url == '/Images/Web/silueta2.gif':  # no photo
            return
        photo_filename = os.path.join(folder, 'photos', str(self.id) + '.jpg')
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
    actor_id = ForeignKeyField(Actor)
    team_id = ForeignKeyField(Team)
    season = IntegerField()
    name = CharField(max_length=510)

    class Meta:
        primary_key = CompositeKey('actor_id', 'team_id', 'season', 'name')

    @staticmethod
    def create_instance(actor_id, team_id, season, actor_name):
        """
        Creates an ActorName object.

        :param actor_id:
        :param actor_name:
        :return:
        """
        ActorName.get_or_create(**{'actor_id': actor_id, 'team_id': team_id, 'season': season, 'name': actor_name})
