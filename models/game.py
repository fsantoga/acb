import os.path, re, datetime, difflib, logging
from pyquery import PyQuery as pq
from src.download import open_or_download, sanity_check_game, sanity_check_game_copa
from models.basemodel import BaseModel, db
from models.team import Team, TeamName
from peewee import (PrimaryKeyField, IntegerField, DateTimeField, ForeignKeyField, BooleanField, CharField)
from src.utils import get_current_season
from tools.log import logger, init_logging
from src.download import open_or_download, get_page
from tools.checkpoint import Checkpoint

init_logging('game.log')

# TODO: move this somewhere else...

ROUND_PHASE_MAPPER = {
            1: "quarter_final",
            2: "semi_final",
            3: "final",
        }


class Game(BaseModel):
    """
    Class representing a Game.

    A game only contains basic information about the game and the scores.
    """
    id = IntegerField(primary_key=True)
    team_home_id = ForeignKeyField(Team, related_name='games_home', index=True, null=True)
    team_away_id = ForeignKeyField(Team, related_name='games_away', index=True, null=True)
    season = IntegerField(null=False)
    competition_phase = CharField(max_length=255, null=True)
    round_phase = CharField(max_length=255, null=True)
    journey = IntegerField(null=False)
    score_home = IntegerField(null=True)
    score_away = IntegerField(null=True)
    score_home_first = IntegerField(null=True)
    score_away_first = IntegerField(null=True)
    score_home_second = IntegerField(null=True)
    score_away_second = IntegerField(null=True)
    score_home_third = IntegerField(null=True)
    score_away_third = IntegerField(null=True)
    score_home_fourth = IntegerField(null=True)
    score_away_fourth = IntegerField(null=True)
    score_home_extra = IntegerField(null=True)
    score_away_extra = IntegerField(null=True)
    venue = CharField(max_length=255, null=True)
    attendance = IntegerField(null=True)
    kickoff_time = DateTimeField(index=True)
    referee_1 = CharField(max_length=255, null=True)
    referee_2 = CharField(max_length=255, null=True)
    referee_3 = CharField(max_length=255, null=True)
    db_flag = BooleanField(null=True)

    @staticmethod
    def download(season):
        """
        Downloads the games of a season.

        How? Finding the games ids.
        Procedure
        ---------
        1. Get journeys ids from http://acb.com/resultados-clasificacion/ver/temporada_id/2017/edicion_id/
        2. Download journeys
        3. Get game ids from each journey: http://acb.com/resultados-clasificacion/ver/temporada_id/2017/edicion_id/undefined/jornada_id/2674
        4. Download games.

        :param season:
        :return:
        """
        def _download_game_webpage(game_id):
            """
            Downloads the game webpage.
            :param game_id:
            :return:
            """
            url = f"http://www.acb.com/partido/estadisticas/id/{game_id}"
            filename = os.path.join(season.GAMES_PATH, f"{game_id}.html")
            open_or_download(file_path=filename, url=url)

        # TODO: En la implementacion anterior hay una distincion si la season es la actual o no. Por que?
        # TODO: ver metodo Game.save_games()
        logger.info(f"Starting to download games for season {season.season}")
        games_ids = Game.get_games_ids(season)
        checkpoint = Checkpoint(length=len(games_ids), chunks=10, msg='already downloaded')

        for game_id in games_ids:
            _download_game_webpage(game_id)
            next(checkpoint)
        logger.info(f"Download finished! (new {len(games_ids)} games in {season.GAMES_PATH})\n")

    @staticmethod
    def get_games_ids(season):
        """
        Get the games ids of a given season.
        :param season:
        :return:
        """
        def _get_journeys_ids(season):
            """
            Gets the journeys ids of a given season
            :param season:
            :return:
            """
            url = f"http://www.acb.com/resultados-clasificacion/ver/temporada_id/{season.season}/edicion_id/"
            filename = os.path.join(season.JOURNEYS_PATH, "journeys-ids.html")
            content = open_or_download(file_path=filename, url=url)
            doc = pq(content)

            journeys_ids = doc("div[class='listado_elementos listado_jornadas bg_gris_claro']").eq(0)
            journeys_ids = journeys_ids('div')
            journeys_ids = [j.attr('data-t2v-id') for j in journeys_ids.items() if j.attr('data-t2v-id')]
            return journeys_ids

        # Get the journeys ids of the season
        journeys_ids = _get_journeys_ids(season)
        games_ids = list()
        for i, journey_id in enumerate(journeys_ids, start=1):
            url = f"http://www.acb.com/resultados-clasificacion/ver/temporada_id/{season.season}/edicion_id/undefined/jornada_id/{journey_id}"
            logger.info(f"Retrieving games from {url}")
            filename = os.path.join(season.JOURNEYS_PATH, f"journey-{i}.html")
            content = open_or_download(file_path=filename, url=url)

            game_ids_journey = re.findall(r'<a href="/partido/estadisticas/id/([0-9]+)" title="Estadísticas">', content, re.DOTALL)
            games_ids.extend(game_ids_journey)
        return games_ids

    @staticmethod
    def create_instances(season):
        games_ids = Game.get_games_ids(season)

        n_regular_games = season.get_number_games_regular_season()
        with db.atomic():
            # Insert games
            for game_number, game_id in enumerate(games_ids):
                competition_phase = 'regular' if game_number < n_regular_games else 'playoff'
                assert game_id != 0
                Game.create_instance(game_id=game_id, season=season, competition_phase=competition_phase)

    @staticmethod
    def create_instance(game_id, season, competition_phase):
        """
        Creates a Game object.

        :param game_id:
        :param season:
        :param competition_phase:
        :return:
        """
        def _get_scores(doc, is_home):
            """
            Get the scores of the team for the game
            :param doc:
            :param is_home:
            :return:
            """
            # Final score
            tag = 'local' if is_home else 'visitante'
            score = doc(f"div[class='resultado {tag} roboto_bold victoria']")
            if not score:
                score = doc(f"div[class='resultado {tag} roboto_bold derrota']")
            score = score.text()
            score = int(score)

            # Partial scores
            partial_scores = {}
            partial_scores_doc = doc('tr')
            tr_id = 1 if is_home else 2
            partial_scores_doc = list(partial_scores_doc.eq(tr_id)('td').items())
            start = 2
            end = len(partial_scores_doc)-1
            while start < end:
                quarter_score = partial_scores_doc[start].text()
                quarter_score = int(quarter_score) if quarter_score else None
                partial_scores[start-1] = quarter_score
                start += 1
            if 5 not in partial_scores:  # add extra time info is missing
                partial_scores[5] = None

            if is_home:
                return {
                    'score_home': score,
                    'score_home_first': partial_scores[1],
                    'score_home_second': partial_scores[2],
                    'score_home_third': partial_scores[3],
                    'score_home_fourth': partial_scores[4],
                    'score_home_extra': partial_scores[5],
                }
            else:
                return {
                    'score_away': score,
                    'score_away_first': partial_scores[1],
                    'score_away_second': partial_scores[2],
                    'score_away_third': partial_scores[3],
                    'score_away_fourth': partial_scores[4],
                    'score_away_extra': partial_scores[5],
                }

        # If the game exists, we do not need to insert it
        query = Game.select().where(Game.id == game_id)
        if query.exists():
            return

        filename = os.path.join(season.GAMES_PATH, game_id + '.html')
        content = open_or_download(file_path=filename)
        doc = pq(content)

        # Season year
        season_year = season.season

        # Teams ids
        teams = doc("div[class='logo_equipo']")
        home_team_id = teams.eq(0)('a').attr('href')
        away_team_id = teams.eq(1)('a').attr('href')
        home_team_id = int(re.search(r'/id/([0-9]+)/', home_team_id).group(1))
        away_team_id = int(re.search(r'/id/([0-9]+)/', away_team_id).group(1))

        # Schedule information
        schedule = doc("div[class='datos_fecha roboto_bold colorweb_4 float-left bg_principal']").text()
        schedule = schedule.split('|')
        schedule = [s.strip() for s in schedule]
        journey, date, time, venue, attendance = schedule

        if date and time:
            day, month, year = list(map(int, date.split("/")))
            hour, minute = list(map(int, time.split(":")))
            kickoff_time = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)

        if attendance:
            attendance = attendance.split(":")[1]
            attendance = attendance.replace('.', '')
            attendance = int(attendance)

        if venue:  # the venue field is duplicated (e.g. Palau BlaugranaPalau Blaugrana)
            assert venue[:len(venue)//2] == venue[len(venue)//2:]
            venue = venue[:len(venue)//2]

        if journey:
            journey = journey.split()[1]
            journey = int(journey)

        # Scores of each team
        results = doc("div[class='info']")
        home_scores = _get_scores(results, is_home=True)
        away_scores = _get_scores(results, is_home=False)

        # Round phase of the game
        if season.competition in ['Copa', 'Supercopa']: # TODO: revisar esto
            round_phase = ROUND_PHASE_MAPPER[journey]
        elif competition_phase == 'playoff':
            round_phase = season.playoff_games_to_phase_mapper[season_year][(home_team_id, away_team_id)]
        else:
            round_phase = None

        game_data = {
            'id': game_id,
            'team_home_id': home_team_id,
            'team_away_id': away_team_id,
            'season': season_year,
            'journey': journey,
            'competition_phase': competition_phase,
            'round_phase': round_phase,
            'venue': venue,
            'attendance': attendance,
            'kickoff_time': kickoff_time,

        }
        game_data.update(home_scores)
        game_data.update(away_scores)
        Game.create(**game_data)

    @staticmethod
    def save_games_copa(season, logging_level=logging.INFO):
        """
        Method for saving locally the games of a season.

        :param season: int
        :param logging_level: logging object
        :return:
        """
        logging.basicConfig(level=logging_level)
        logger = logging.getLogger(__name__)

        logger.info('Starting the download of games...')

        if season.season == get_current_season():
            current_game_events_ids = season.get_current_game_events_ids_copa()
            game_ids_list = list(current_game_events_ids.values())
        else:
            game_ids_list=season.get_game_ids_copa()

        n_checkpoints = 4
        checkpoints = [round(i * float(len(game_ids_list)) / n_checkpoints) for i in range(n_checkpoints + 1)]
        for i in range(len(game_ids_list)):

            game_id=int(game_ids_list[i]) % 1000
            url2 = BASE_URL + "/fichas/CREY{}.php".format(game_ids_list[i])
            filename = os.path.join(season.GAMES_COPA_PATH, str(game_id)+"-" +str(game_ids_list[i]) + '.html')

            open_or_download(file_path=filename, url=url2)
            if i in checkpoints:
                logger.info('{}% already downloaded'.format(round(float(i * 100) / len(game_ids_list))))

        logger.info('Download finished! (new {} games in {})\n'.format(len(game_ids_list), season.GAMES_COPA_PATH))

    @staticmethod
    def sanity_check(season, logging_level=logging.INFO):
        sanity_check_game(season.GAMES_PATH, logging_level)

    @staticmethod
    def sanity_check_copa(season, logging_level=logging.INFO):
        sanity_check_game_copa(season.GAMES_COPA_PATH, logging_level)