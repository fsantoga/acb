import os.path, re, datetime, difflib, logging
from pyquery import PyQuery as pq
# from src.download import open_or_download, sanity_check_game, sanity_check_game_copa
from models.basemodel import BaseModel, db
from models.team import Team, TeamName
from peewee import (PrimaryKeyField, IntegerField, DateTimeField, ForeignKeyField, BooleanField, CharField)
from tools.log import logger, init_logging
from src.download import DownloadManager, File
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
    db_flag = BooleanField(null=True, default=False)

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
            file = File(filename)
            file.open_or_download(url=url, download_manager=dm)

        # Download manager object
        dm = DownloadManager()

        logger.info(f"Starting to download games for season {season.season}")
        games_ids = Game.get_games_ids(season, download_manager=dm)
        checkpoint = Checkpoint(length=len(games_ids), chunks=10, msg='already downloaded')

        for game_id in games_ids:
            _download_game_webpage(game_id)
            next(checkpoint)
        logger.info(f"Download finished! (new {len(games_ids)} games in {season.GAMES_PATH})\n")

    @staticmethod
    def get_teams(game_file):
        def _get_team(game_file, is_home):
            file = File(game_file)
            content = file.open()
            doc = pq(content)
            doc = doc("div[class='contenedora_info_principal']")
            tag = 0 if is_home else 1

            team_id = doc("div[class='logo_equipo']").eq(tag)('a').attr('href')
            team_id = re.search(r'/club/plantilla/id/([0-9]+)/', team_id).group(1)
            return team_id
        home_team = _get_team(game_file, is_home=True)
        away_team = _get_team(game_file, is_home=False)
        return home_team, away_team

    @staticmethod
    def get_games_ids(season, download_manager=None):
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
            file = File(filename)
            content = file.open_or_download(url=url, download_manager=download_manager)
            doc = pq(content)

            journeys_ids = doc("div[class='listado_elementos listado_jornadas bg_gris_claro']").eq(0)
            journeys_ids = journeys_ids('div')

            journeys_numbers = [j.text() for j in journeys_ids.items() if j.attr('data-t2v-id')]
            journeys_numbers = [int(j.split()[-1]) for j in journeys_numbers]
            journeys_ids = [j.attr('data-t2v-id') for j in journeys_ids.items() if j.attr('data-t2v-id')]
            journeys_ids = dict(zip(journeys_numbers, journeys_ids))

            def find_missing(lst):
                return sorted(set(range(lst[0], lst[-1])) - set(lst))
            missing_journeys = find_missing(journeys_numbers)

            for n in missing_journeys:
                journeys_ids[n] = None

            return journeys_ids

        # Get the journeys ids of the season
        journeys_ids = _get_journeys_ids(season)
        games_ids = list()
        for i, journey_id in journeys_ids.items():
            if season.current_journey and i == season.current_journey:  # no info about current journey
                break

            url = f"http://www.acb.com/resultados-clasificacion/ver/temporada_id/{season.season}/edicion_id/undefined/jornada_id/{journey_id}"
            logger.info(f"Retrieving games from {url}")
            filename = os.path.join(season.JOURNEYS_PATH, f"journey-{i}.html")
            file = File(filename)
            content = file.open_or_download(url=url, download_manager=download_manager)
            game_ids_journey = re.findall(r'<a href="/partido/estadisticas/id/([0-9]+)" title="Estadísticas">', content, re.DOTALL)

            if len(game_ids_journey) == 0 and season.is_current_season():
                file.delete()
                season.current_journey = i
                logger.warning(f"There are no new games for season {season.season} and journey {i}")
                break
            games_ids.extend(game_ids_journey)
        else:
            season.current_journey = len(journeys_ids)

        return games_ids

    @staticmethod
    def create_instances(season):
        """
        Inserts all the games of a season in the database.

        :param season:
        :return:
        """
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

        Example from: acb.com/partido/estadisticas/id/18102

        :param game_id:
        :param season:
        :param competition_phase:
        :return:
        """
        def _get_scores(doc, is_home):
            """
            Get the scores of the team for the game.

            :param doc:
            :param is_home:
            :return:
            """
            # Final score
            # <div class="resultado local roboto_bold victoria">87</div>
            # <div class="resultado visitante roboto_bold derrota">70</div>
            tag = 'local' if is_home else 'visitante'
            score = doc(f"div[class='resultado {tag} roboto_bold victoria']")
            if not score:
                score = doc(f"div[class='resultado {tag} roboto_bold derrota']")
            score = score.text()
            score = int(score)

            # Partial scores
            # <tr>
            #   <th>&nbsp;</th>
            #   <th>&nbsp;</th>
            #   <th>1</th>
            #   <th>2</th>
            #   <th>3</th>
            #   <th>4</th>
            # </tr>
            # <tr>
            #   <td class="equipo mayusculas victoria">KIR</td>
            #   <td class="blanco">&nbsp;</td>
            #   <td class="parcial victoria">18</td>
            #   <td class="parcial victoria">26</td>
            #   <td class="parcial derrota">15</td>
            #   <td class="parcial victoria">28</td>
            #   <td class="blanco">&nbsp;</td>
            # </tr>
            # <tr>
            #   <td class="equipo mayusculas derrota">UNI</td>
            #   <td class="blanco">&nbsp;</td>
            #   <td class="parcial derrota">16</td>
            #   <td class="parcial derrota">20</td>
            #   <td class="parcial victoria">20</td>
            #   <td class="parcial derrota">14</td>
            #   <td class="blanco">&nbsp;</td>
            # </tr>
            partial_scores = {}
            partial_scores_doc = doc('tr')
            tr_id = 1 if is_home else 2  # index 0 is junk data
            partial_scores_doc = list(partial_scores_doc.eq(tr_id)('td').items())
            start = 2  # omit first two td
            end = len(partial_scores_doc)-1  # omit last td
            quarter = 1
            while start < end:
                quarter_score = partial_scores_doc[start].text()
                quarter_score = int(quarter_score) if quarter_score else None
                partial_scores[quarter] = quarter_score
                quarter += 1
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
        file = File(filename)
        content = file.open()
        doc = pq(content)

        # Season year
        season_year = season.season

        # Teams ids
        # <div class="logo_equipo">
        #   <a href="/club/plantilla/id/3/equipo-KIROLBET-BASKONIA">
        # <div class="logo_equipo">
        #   <a href="/club/plantilla/id/14/equipo-UNICAJA">
        teams = doc("div[class='logo_equipo']")
        home_team_id = teams.eq(0)('a').attr('href')
        away_team_id = teams.eq(1)('a').attr('href')
        home_team_id = int(re.search(r'/id/([0-9]+)/', home_team_id).group(1))
        away_team_id = int(re.search(r'/id/([0-9]+)/', away_team_id).group(1))

        # Schedule information
        # <div class="datos_fecha roboto_bold colorweb_4 float-left bg_principal">
        # JORNADA 35 | 27/05/2018 | 18:30<span class="clase_mostrar768"> |
        # </span><br class="clase_ocultar_768" /><span class="clase_ocultar_1280">Fernando Buesa Arena</span>
        # <span class="clase_mostrar1280">Fernando Buesa Arena</span> | Público: 10.084</div>
        schedule = doc("div[class='datos_fecha roboto_bold colorweb_4 float-left bg_principal']").text()
        schedule = schedule.split('|')
        schedule = [s.strip() for s in schedule]
        journey, date, time, venue, attendance = schedule
        kickoff_time = None

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

    # @staticmethod
    # def save_games_copa(season, logging_level=logging.INFO):
    #     """
    #     Method for saving locally the games of a season.
    #
    #     :param season: int
    #     :param logging_level: logging object
    #     :return:
    #     """
    #     logging.basicConfig(level=logging_level)
    #     logger = logging.getLogger(__name__)
    #
    #     logger.info('Starting the download of games...')
    #
    #     if season.season == get_current_season():
    #         current_game_events_ids = season.get_current_game_events_ids_copa()
    #         game_ids_list = list(current_game_events_ids.values())
    #     else:
    #         game_ids_list=season.get_game_ids_copa()
    #
    #     n_checkpoints = 4
    #     checkpoints = [round(i * float(len(game_ids_list)) / n_checkpoints) for i in range(n_checkpoints + 1)]
    #     for i in range(len(game_ids_list)):
    #
    #         game_id=int(game_ids_list[i]) % 1000
    #         url2 = BASE_URL + "/fichas/CREY{}.php".format(game_ids_list[i])
    #         filename = os.path.join(season.GAMES_COPA_PATH, str(game_id)+"-" +str(game_ids_list[i]) + '.html')
    #
    #         open_or_download(file_path=filename, url=url2)
    #         if i in checkpoints:
    #             logger.info('{}% already downloaded'.format(round(float(i * 100) / len(game_ids_list))))
    #
    #     logger.info('Download finished! (new {} games in {})\n'.format(len(game_ids_list), season.GAMES_COPA_PATH))
    #
    # @staticmethod
    # def sanity_check(season, logging_level=logging.INFO):
    #     sanity_check_game(season.GAMES_PATH, logging_level)
    #
    # @staticmethod
    # def sanity_check_copa(season, logging_level=logging.INFO):
    #     sanity_check_game_copa(season.GAMES_COPA_PATH, logging_level)