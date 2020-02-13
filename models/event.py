import os.path, re, difflib
from models.basemodel import BaseModel, db
from models.team import Team
from models.actor import Actor
from src.utils import convert_time, create_driver, get_driver_path
from pyquery import PyQuery as pq
from peewee import (PrimaryKeyField, ForeignKeyField, CharField, TextField, IntegerField)
from tools.checkpoint import Checkpoint
from models.team import TeamName
from models.game import Game
from models.participant import Participant
from models.actor import ActorName
from fuzzywuzzy import fuzz, process
from tools.log import logger
from src.download import DownloadManager, File


legend_dict = {
    'Asistencia': 'assist',
    'Tapón': 'block',
    'Recuperación': 'steal',
    'Pérdida': 'turnover',
    'Pérdida en el manejo del balón': 'turnover',
    'Pérdida por campo atrás': 'turnover',
    'Pérdida por 3 segundos': 'turnover',
    'Pérdida por 3seg.': 'turnover',
    'Pérdida por 5 segundos': 'turnover',
    'Pérdida por 5seg.': 'turnover',
    'Pérdida por falta en ataque': 'turnover',
    'Pérdida por fuera de banda': 'turnover',
    'Pérdida por mal pase': 'turnover',
    'Pérdida por pasos': 'turnover',
    'Pérdida por interferencia en ataque': 'turnover',
    'Pérdida por 24 segundos': 'turnover',
    'Pérdida por 24seg.': 'turnover',
    'Pérdida por 8 segundos': 'turnover',
    'Pérdida por 8seg.': 'turnover',
    'Pérdida por dobles': 'turnover',
    'TIEMPO MUERTO': 'timeout',
    'TIEMPO MUERTO TV': 'timeout_tv',
    'TIEMPO MUERTO CORTO': 'timeout',
    'TIEMPO MUERTO ARBITRAJE': 'timeout',
    'Salto balón retenido': 'salto',
    'Falta antideportiva': 'foul',
    'Falta en ataque': 'foul',
    'Falta personal': 'foul',
    'Falta recibida': 'foul_rv',
    'Falta técnica': 'foul',
    'foul': 'foul',
    'Falta descalificante': 'foul',
    'Técnica al banquillo': 'foul',
    'Técnica al entrenador': 'foul',
    'Rebote ofensivo': 'reb_off',
    'Rebote defensivo': 'reb_def',
    'Entra a pista': 'sub_in',
    'Se retira': 'sub_out',
    'Tiro libre 1/1 convertido': 'made1',
    'Tiro libre 1/1 fallado': 'miss1',
    'Tiro libre 1/2 convertido': 'made1',
    'Tiro libre 1/2 fallado': 'miss1',
    'Tiro libre 1/3 fallado': 'miss1',
    'Tiro libre 1/3 convertido': 'made1',
    'Tiro libre 2/2 convertido': 'made1',
    'Tiro libre 2/2 fallado': 'miss1',
    'Tiro libre 2/3 convertido': 'made1',
    'Tiro libre 2/3 fallado': 'miss1',
    'Tiro libre 3/3 convertido': 'made1',
    'Tiro libre 3/3 fallado': 'miss1',
    '2PT bandeja convertido': 'made2',
    '2PT bandeja fallado': 'miss2',
    '2PT bandeja en penetración convertido': 'made2',
    '2PT bandeja en penetración fallado': 'miss2',
    '2PT palmeo convertido': 'made2',
    '2PT palmeo fallado': 'miss2',
    '2PT tiro convertido': 'made2',
    '2PT tiro sobre bote convertido': 'made2',
    '2PT tiro sobre bote fallado': 'miss2',
    '2PT tiro con paso atrás convertido': 'made2',
    '2PT tiro con paso atrás fallado': 'miss2',
    '2PT tiro elevado convertido': 'made2',
    '2PT tiro elevado fallado': 'miss2',
    'Mate convertido': 'made2',
    'Mate fallado': 'miss2',
    '2PT tiro fallado': 'miss2',
    '2PT Alley oop convertido': 'made2',
    '2PT Alley-oop convertido': 'made2',
    '2PT Alley oop fallado': 'miss2',
    '2PT gancho convertido': 'made2',
    '2PT gancho fallado': 'miss2',
    '2PT tiro a la media vuelta convertido': 'made2',
    '2PT tiro a la media vuelta fallado': 'miss2',
    '2PT Tiro en caída convertido': 'made2',
    '2PT Tiro en caída fallado': 'miss2',
    '3PT convertido': 'made3',
    '3PT tiro en suspensión convertido': 'made3',
    '3PT fallado': 'miss3',
    '3PT tiro en suspensión fallado': 'miss3',
    '3PT tiro elevado convertido': 'made3',
    '3PT tiro elevado fallado': 'miss3',
    '3PT tiro a la media vuelta convertido': 'made3',
    '3PT tiro a la media vuelta fallado': 'miss3',
    '3PT tiro en caída convertido': 'made3',
    '3PT tiro en caída fallado': 'miss3',
    '3PT tiro sobre bote convertido': 'made3',
    '3PT tiro sobre bote fallado': 'miss3',
    '3PT tiro con paso atrás convertido': 'made3',
    '3PT tiro con paso atrás fallado': 'miss3',
    'Salto ganado': 'tipoff_won',
    'Salto perdido': 'tipoff_lost',
    'COMIENZA EL PARTIDO': 'game_start',
    'PARTIDO FINALIZADO': 'game_end',
    'INICIO PERIODO': 'quarter_start',
    'jumpball.unclearposs': 'jumpball_unclearposs',
    'BASKETBALL_ACTION_3PT_JUMPSHOT convertido': 'made3',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT convertido': 'made2',
    'BASKETBALL_ACTION_2PT_HOOKSHOT convertido': 'made2',
    'BASKETBALL_ACTION_3PT_JUMPSHOT fallado': 'miss3',
    'BASKETBALL_ACTION_2PT_HOOKSHOT fallado': 'miss2',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT fallado': 'miss2',
    'BASKETBALL_ACTION_TURNOVER_OTHER': 'turnover',
    'PERIODO FINALIZADO': 'quarter_end',

}

extra_legend_dict = {
    'TIEMPO MUERTO CORTO': 'short',
    'TIEMPO MUERTO ARBITRAJE': 'referee',
    'Pérdida en el manejo del balón': 'ballhandling',
    'Pérdida por campo atrás': 'backcourt',
    'Pérdida por 3 segundos': '3_seconds',
    'Pérdida por 3seg.': '3_seconds',
    'Pérdida por falta en ataque': 'offensive_foul',
    'Pérdida por fuera de banda': 'out_of_bounds',
    'Pérdida por mal pase': 'bad_pass',
    'Pérdida por pasos': 'travelling',
    'Pérdida por interferencia en ataque': 'goaltending',
    'Pérdida por 24 segundos': '24_seconds',
    'Pérdida por 24seg.': '24_seconds',
    'Pérdida por 5 segundos': '5_seconds',
    'Pérdida por 5seg.': '5_seconds',
    'Pérdida por 8 segundos': '8_seconds',
    'Pérdida por 8seg.': '8_seconds',
    'Pérdida por dobles': 'double_dribble',
    'Falta antideportiva': 'flagrant',
    'Falta en ataque': 'offensive',
    'Falta técnica': 'technical',
    'Falta descalificante': 'disqualifying',
    'Técnica al banquillo': 'bench_technical',
    'Técnica al entrenador':  'coach_technical',
    'Tiro libre 1/1 convertido': '1/1',
    'Tiro libre 1/1 fallado': '1/1',
    'Tiro libre 1/2 convertido': '1/2',
    'Tiro libre 1/2 fallado': '1/2',
    'Tiro libre 1/3 convertido': '1/3',
    'Tiro libre 1/3 fallado': '1/3',
    'Tiro libre 2/2 convertido': '2/2',
    'Tiro libre 2/2 fallado': '2/2',
    'Tiro libre 2/3 convertido': '2/3',
    'Tiro libre 2/3 fallado': '2/3',
    'Tiro libre 3/3 convertido': '3/3',
    'Tiro libre 3/3 fallado': '3/3',
    '2PT bandeja convertido': 'layup',
    '2PT bandeja fallado': 'layup',
    '2PT bandeja en penetración convertido': 'layup',
    '2PT bandeja en penetración fallado': 'layup',
    '2PT palmeo convertido': 'tip',
    '2PT palmeo fallado': 'tip',
    '2PT tiro con paso atrás convertido': 'stepback',
    '2PT tiro con paso atrás fallado': 'stepback',
    '2PT tiro convertido': 'jumpshot',
    '2PT Alley oop convertido': 'alleyhoop',
    '2PT Alley-oop convertido': 'alleyhoop',
    '2PT Alley oop fallado': 'alleyhoop',
    '2PT gancho convertido': 'hook',
    '2PT gancho fallado': 'hook',
    '2PT tiro a la media vuelta convertido': 'fadeway',
    '2PT tiro a la media vuelta fallado': 'fadeway',
    '3PT tiro a la media vuelta convertido': 'fadeway',
    '3PT tiro a la media vuelta fallado': 'fadeway',
    '3PT tiro con paso atrás fallado': 'stepback',
    '3PT tiro con paso atrás convertido': 'stepback',
    'Mate convertido': 'dunk',
    'Mate fallado': 'dunk',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT convertido': 'stepback',
    'BASKETBALL_ACTION_2PT_HOOKSHOT convertido': 'hookshot',
    'BASKETBALL_ACTION_2PT_HOOKSHOT fallado': 'hookshot',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT fallado': 'stepback',
}


class Event(BaseModel):
    id = PrimaryKeyField()
    event_id = IntegerField()
    game_id = IntegerField(index=True)
    team_id = ForeignKeyField(Team, index=False, null=True)
    legend = TextField(null=True)
    extra_info = TextField(null=True)
    elapsed_time = IntegerField(null=True)
    jersey = IntegerField(null=True)
    actor_id = ForeignKeyField(Actor, index=False, null=True)
    home_score = IntegerField(null=True)
    away_score = IntegerField(null=True)

    @staticmethod
    def download(season):
        def _download_event_webpage(event_id, download_manager):
            """
            Downloads the event webpage.
            :param game_id:
            :return:
            """
            url = f"http://www.fibalivestats.com/u/ACBS/{event_id}/pbp.html"
            filename = os.path.join(season.EVENTS_PATH, f"{str(event_id)}.html")
            file = File(filename)
            file.open_or_download(url=url, download_manager=download_manager, driver=True)

        # Download manager object
        driver_path = get_driver_path()
        driver = create_driver(driver_path)
        dm = DownloadManager(driver=driver)

        # Get the events ids. For the current season, only until current journey...
        events_ids = Event.get_events_ids(season, download_manager=dm)

        checkpoint = Checkpoint(length=len(events_ids), chunks=10, msg='already downloaded')
        for (_, event_id) in events_ids:
            _download_event_webpage(event_id, dm)
            next(checkpoint)

    @staticmethod
    def get_events_ids(season, download_manager=None):
        events_ids = []
        for i in range(1, season.current_journey + 1):
            url = f"http://jv.acb.com/historico.php?jornada={i}&cod_competicion=LACB&cod_edicion={season.season_id}"
            filename = os.path.join(season.EVENTS_PATH, 'journeys', f"journey-{i}.html")
            file = File(filename)
            content = file.open_or_download(url=url, download_manager=download_manager)

            fls_ids = re.findall(r'<div class="partido borde_azul" id="partido-([0-9]+)">', content, re.DOTALL)
            fls_ids = [(i, fls) for fls in fls_ids]
            events_ids.extend(fls_ids)
        return events_ids

    @staticmethod
    def create_instances(season):
        events_ids = Event.get_events_ids(season)
        with db.atomic():
            for (journey_id, event_id) in events_ids:
                Event.create_instance(season, journey_id, event_id)

    @staticmethod
    def create_instance(season, journey_id, event_id):
        # TODO comprobar que los eventos de ese partido ya se han metido en db
        # TODO, seguramente crear un atributo como db_flag. Quizas reutilizar esE?

        filename = os.path.join(season.EVENTS_PATH, event_id + '.html')
        file = File(filename)
        content = file.open()
        doc = pq(content)

        home_team = doc('span[class="id_aj_1_name"]').text()
        away_team = doc('span[class="id_aj_2_name"]').text()

        if home_team == away_team == '':
            teams = doc('meta[name="twitter:title"]').attr('content')
            home_team, away_team = teams.split('v')
            home_team = home_team.strip()
            away_team = away_team.strip()
        print(event_id, home_team)
        home_team_id = TeamName.get(name=home_team).team_id.id
        print(away_team)
        away_team_id = TeamName.get(name=away_team).team_id.id

        game = Game.get(team_home_id=home_team_id, team_away_id=away_team_id, season=season.season, journey=journey_id)
        game_id = game.id

        print(home_team, home_team_id, away_team, away_team_id, event_id, game_id)

        # If there are events for that game, we do not need to insert them
        query = Event.select().where(Event.game_id == game_id)
        if query.exists():
            return

        home_actors = Participant.select(Participant.actor, Participant.display_name).where(
            (Participant.game == game_id) & (Participant.team == home_team_id))
        home_actors = {q.display_name: q.actor.id for q in home_actors}

        away_actors = Participant.select(Participant.actor, Participant.display_name).where(
            (Participant.game == game_id) & (Participant.team == away_team_id))
        away_actors = {q.display_name: q.actor.id for q in away_actors}


        playbyplay = doc('div[id="playbyplay"]')
        events = list()
        home_score = away_score = 0
        time = '10:00'
        period = 'P1'

        for elem in reversed(list(playbyplay('div').items())):
            if not elem.attr['id'] or elem.attr['id'] in ['playbyplay', 'aj_pbp']:
                continue
            tag = elem.attr['class']
            is_timeout = False

            if 'pbpa pbpt0' in tag:
                is_timeout = True
            elif 'pbpa pbpt1' in tag:
                team_id = home_team_id
                actors = home_actors
            elif 'pbpa pbpt2' in tag:
                team_id = away_team_id
                actors = away_actors
            else:
                raise Exception

            # Remove last line of this type of events:
            # 23, C. Evans, Mate convertido
            # HERBALIFE GRAN CANARIA - gana por 1
            if is_timeout:
                legend = elem.text().split("\n")[0]
                jersey = None
                display_name = None
                team_id = None
            else:
                legend = elem('.pbp-action').text().split("\n")[0]
                if ',' in legend:
                    jersey, display_name, legend = legend.split(", ")
                else:
                    jersey, display_name, legend = None, None, legend
                period = elem('.pbp-period').text()
                time = elem.attr['id']

            if elem('.pbpsc'):
                home_score, away_score = elem('.pbpsc').text().split('-')

            if not display_name:
                actor_id = None
            elif display_name in actors.keys():
                actor_id = actors[display_name]
            else:
                try:
                    actor = ActorName.get(**{'team_id': team_id, 'season': season.season, 'name': display_name})
                    actor_id = actor.actor_id.id
                except ActorName.DoesNotExist:
                    most_likely_coincide, threshold = process.extractOne(display_name, actors.keys(),
                                                                         scorer=fuzz.token_set_ratio)
                    logger.warning(
                        f"actor {display_name} was match to {most_likely_coincide} with threshold {threshold}")
                    assert threshold > 72, f"the threshold {threshold} is too low for {display_name} and match: {most_likely_coincide} {type(team_id)}{team_id} {actors.keys()}"
                    actor_id = actors[most_likely_coincide]
                    ActorName.create_instance(actor_id=actor_id, team_id=team_id, season=season.season, actor_name=display_name)

            elapsed_time = convert_time(time, period)
            events.append({"event_id": event_id,
                           "game_id": game_id,
                           "team_id": team_id,
                           "actor_id": actor_id,
                           "legend": legend_dict[legend],
                           "extra_info": extra_legend_dict.setdefault(legend, None),
                           "elapsed_time": elapsed_time,
                           "jersey": jersey,
                           "home_score": home_score,
                           "away_score": away_score,
                           })

        with db.atomic():
            for event in events:
                Event.create(**event)
        db.commit()



    #
    # @staticmethod
    # def scrap_and_insert(events_game_acbid, game_acbid, playbyplay, team_home_id, team_away_id, actors_home, actors_away):
    #     actions = {}
    #     cont = 1
    #     events_with_errors=0
    #     home_score = away_score = 0
    #
    #     roster_home=[]
    #     roster_away=[]
    #
    #
    #     for elem in reversed(list(playbyplay('div').items())):
    #         if elem.attr['class'] and elem.attr['class'].startswith("pbpa"):
    #
    #             tag = elem.attr['class']
    #             team_id = team_home_id if "pbpt1" in tag else team_away_id if "pbpt2" in tag else None
    #
    #             try:
    #                 legend = elem('.pbp-action').text().split(", ")[-1].split("\n")[0]
    #                 period, boxscore = elem('.pbp-time').text().split(" ")
    #                 boxscore_search = re.search(r'([0-9]{2}:[0-9]{2})([0-9]+)-([0-9]+)', boxscore)
    #                 if boxscore_search:
    #                     time, home_score, away_score = boxscore_search.groups()
    #                 else:
    #                     time = re.search(r'([0-9]{2}:[0-9]{2})', boxscore).groups()[0]
    #                 jersey, display_name, _ = elem('.pbp-action').text().split(", ")
    #                 jersey = int(jersey)
    #
    #                 # Matching display_name with actor_id
    #                 if team_id == team_home_id:
    #                     actors_names_ids = actors_home
    #                 elif team_id == team_away_id:
    #                     actors_names_ids = actors_away
    #                 else:
    #                     actors_names_ids = None
    #
    #                 if display_name in actors_names_ids.keys():
    #                     query_actor_id = actors_names_ids[display_name]
    #                 else:
    #                     most_likely_actor = difflib.get_close_matches(display_name, actors_names_ids.keys(), 1, 0.4)[0]
    #                     query_actor_id = actors_names_ids[most_likely_actor]
    #                     logger.info('Actor {} has been matched to: {}'.format(display_name, most_likely_actor))
    #
    #             except:  # Cells without player associated (e.g. timeouts and missing info)
    #                 legend = elem('.pbp-action').text() if elem('.pbp-action').text() != '' else elem.text().split("\n")[0]
    #                 time = elem.attr['id']
    #                 period = "P" + re.search(r'per_[a-z]?([a-z]?[0-9]+)', tag).groups()[0]
    #                 jersey = -1
    #                 query_actor_id=None
    #
    #             #roster home
    #             if "pbpt1" in tag:
    #                 if legend_dict[legend]=="sub_in":
    #                     if query_actor_id not in roster_home:
    #                         roster_home.append(query_actor_id)
    #                 elif legend_dict[legend]=="sub_out":
    #                     try:
    #                         roster_home.remove(query_actor_id)
    #                     except:
    #                         logger.warning('Game: {} ({}). Cannot remove actor. Actor {} is not in list {}'.format(game_acbid, events_game_acbid, query_actor_id, roster_home))
    #
    #             #roster away
    #             elif "pbpt2" in tag:
    #                 if legend_dict[legend]=="sub_in":
    #                     if query_actor_id not in roster_away:
    #                         roster_away.append(query_actor_id)
    #                 elif legend_dict[legend]=="sub_out":
    #                     try:
    #                         roster_away.remove(query_actor_id)
    #                     except:
    #                         logger.warning('Game: {} ({}). Cannot remove actor. Actor {} is not in list {}'.format(game_acbid, events_game_acbid, query_actor_id, roster_away))
    #
    #             if legend in play_events_dict:
    #                 if len(roster_home) != 5:
    #                     events_with_errors+=1
    #                     logger.warning('Game: {} ({}). Roster home list length ({}) error: {} for team: {} and event: {}'.format(game_acbid,events_game_acbid,len(roster_home),roster_home,team_home_id,legend_dict[legend]))
    #                 if len(roster_away) != 5:
    #                     events_with_errors += 1
    #                     logger.warning('Game: {} ({}). Roster away list length ({}) error: {} for team: {} and event: {}'.format(game_acbid,events_game_acbid,len(roster_away),roster_away,team_away_id,legend_dict[legend]))
    #                 #if query_actor_id not in roster_home and query_actor_id not in roster_away:
    #                     #if jersey is not -1:
    #                     #logger.warning('Game: {} ({}). The actor: {} with jersey: {} is not in the field for event: {}. Roster home {}, Roster away: {}'.format(game_acbid,events_game_acbid,query_actor_id,jersey,legend_dict[legend],roster_home,roster_away))
    #
    #             elapsed_time = convert_time(time, period[1:])
    #             actions[cont] = {"events_game_acbid": events_game_acbid,
    #                              "game_acbid": game_acbid,
    #                              "team_id": team_id,
    #                              "actor_id": query_actor_id,
    #                              "legend": legend_dict[legend],
    #                              "extra_info": extra_legend_dict.setdefault(legend, None),
    #                              "elapsed_time": elapsed_time,
    #                              "jersey": jersey,
    #                              "home_score": home_score,
    #                              "away_score": away_score,
    #                              "roster_home": str(roster_home),
    #                              "roster_away": str(roster_away)}
    #             cont+=1
    #
    #     with db.atomic():
    #         for event in actions.values():
    #             Event.create(**event)
    #
    #     return events_with_errors
    #
    # @staticmethod
    # def _fix_short_roster(game_acbid, roster_home_or_away, roster, list_include_actor, legend):
    #     if roster_home_or_away==0:
    #         try:
    #             wrong_roster = Event.get((Event.game_acbid==game_acbid) & (Event.roster_home==roster) & (Event.legend==legend))
    #             roster_list = ast.literal_eval(roster)
    #             for elem in list_include_actor:
    #                 roster_list.append(elem)
    #
    #             wrong_roster.roster_home = roster_list
    #             wrong_roster.save()
    #
    #         except Event.DoesNotExist:
    #             pass
    #
    #     elif roster_home_or_away==1:
    #         try:
    #             wrong_roster = Event.get((Event.game_acbid==game_acbid) & (Event.roster_away==roster) & (Event.legend==legend))
    #             roster_list = ast.literal_eval(roster)
    #             for elem in list_include_actor:
    #                 roster_list.append(elem)
    #
    #             wrong_roster.roster_away = roster_list
    #             wrong_roster.save()
    #
    #         except Event.DoesNotExist:
    #             pass
    #
    # """
    # @staticmethod
    # def _fix_long_roster(game_acbid, team_id,roster_length,list_include_actor):
    #     try:
    #         wrong_participant = Participant.get(
    #             (Participant.display_name == "") & (Participant.team == team_id) & (Participant.is_coach == 0) & (
    #             Participant.number == number))
    #         wrong_participant.delete_instance()
    #
    #     except Participant.DoesNotExist:
    #         pass
    # """
    #
    # @staticmethod
    # def _check_rosters():
    #     logging.basicConfig(level=logging.INFO)
    #     logger = logging.getLogger(__name__)
    #
    #     logger.info('Starting the roster checking...')
    #
    #     query = Event.select().dicts()
    #
    #     for row in query:
    #         if row['legend'] in play_events_dict.values():
    #             roster_home_list = ast.literal_eval(row['roster_home'])
    #             roster_away_list = ast.literal_eval(row['roster_away'])
    #
    #             if len(roster_home_list) != 5:
    #                 logger.warning(
    #                     'Game: {} ({}). Roster home list length ({}) error: {} for team: {} and event: {}'.format(
    #                         row['game_acbid'], row['events_game_acbid'], len(roster_home_list), row['roster_home'], row['team_id'],
    #                         row['legend']))
    #             if len(roster_away_list) != 5:
    #                 logger.warning(
    #                     'Game: {} ({}). Roster away list length ({}) error: {} for team: {} and event: {}'.format(
    #                         row['game_acbid'], row['events_game_acbid'], len(roster_away_list), row['roster_away'], row['team_id'],
    #                         row['legend']))
    #
    # @staticmethod
    # def fix_rosters():
    #     logging.basicConfig(level=logging.INFO)
    #     logger = logging.getLogger(__name__)
    #
    #     logger.info('Starting the roster fixing...')
    #
    #     Event._fix_short_roster(63018,0,"[24, 18, 25, 15]",[10],"turnover")
    #     Event._fix_short_roster(63018,0,"[24, 18, 25, 15]",[10],"steal")
    #
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"steal")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss1")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"block")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"assist")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"steal")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_off")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"steal")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_off")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"assist")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"reb_def")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"assist")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"miss1")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"miss1")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"turnover")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"miss3")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"reb_off")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"miss2")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"reb_off")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made2")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"assist")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"foul")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"foul_rv")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made1")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"miss1")
    #     Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"reb_def")
    #
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "tipoff_won")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "tipoff_won")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "tipoff_lost")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "tipoff_lost")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "turnover")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "turnover")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "steal")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "steal")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul_rv")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul_rv")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made3")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254],"made2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul_rv")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul_rv")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "turnover")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "turnover")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made3")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "turnover")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "turnover")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul_rv")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul_rv")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_off")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_off")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "block")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "block")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_off")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_off")
    #     Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
    #     Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[]", [220, 212, 216, 218, 254], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[]", [41, 43, 49, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul")
    #     Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul_rv")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul_rv")
    #     Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "miss1")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "miss1")
    #     Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "made1")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "made1")
    #     Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "assist")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "assist")
    #     Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul")
    #     Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul_rv")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul_rv")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss3")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made3")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "made3")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss2")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "turnover")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "turnover")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul_rv")
    #     Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul_rv")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss2")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_off")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "reb_off")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "made2")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss3")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "miss3")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_off")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "reb_off")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "foul")
    #     Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul_rv")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "foul_rv")
    #     Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "miss2")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "reb_def")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "reb_def")
    #     Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "miss2")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "miss2")
    #     Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "reb_off")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "reb_off")
    #     Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "made2")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "made2")
    #     Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "turnover")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "turnover")
    #     Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "made2")
    #
    #     Event._fix_short_roster(63086,1,"[177, 184, 180, 182]",[176],"reb_off")
    #
    #     Event._fix_short_roster(63048,1,"[232, 227, 233, 225]",[229],"miss1")
    #     Event._fix_short_roster(63048,1,"[232, 227, 233, 225]",[229],"made1")
    #     Event._fix_short_roster(63048,0,"[43, 51, 45, 41]",[49],"made1")
    #
    #     Event._fix_short_roster(63160,0,"[128, 121, 117, 119]",[126],"reb_def")
    #
    #     Event._fix_short_roster(63050,1,"[16, 24, 25, 15]",[14],"miss3")
    #
    #     Event._fix_short_roster(63123,0,"[14, 171, 24, 25]",[16],"made1")
    #     Event._fix_short_roster(63123,0,"[14, 171, 24, 25]",[16],"made1")
    #     Event._fix_short_roster(63123,0,"[14, 171, 24, 25]",[16],"assist")
    #
    #     Event._fix_short_roster(63031,1,"[254, 214, 221, 222]",[216],"miss3")
    #
    #     Event._fix_short_roster(63159,0,"[86, 124, 82, 89]",[79],"made1")
    #
    #     Event._fix_short_roster(63008,0,"[51, 42, 47, 49]",[41],"made1")
    #     Event._fix_short_roster(63008,0,"[41, 43, 46, 42]",[51],"made1")
    #     Event._fix_short_roster(63008,0,"[41, 43, 46, 42]",[51],"made1")
    #
    #     Event._fix_short_roster(63029,1,"[77, 240, 72, 67]",[74],"made1")
    #     Event._fix_short_roster(63029,1,"[77, 240, 72, 67]",[74],"made1")
    #     Event._fix_short_roster(63029,1,"[75, 70, 74, 71]",[67],"made1")
    #     Event._fix_short_roster(63029,1,"[75, 70, 74, 71]",[67],"made1")
    #
    #     Event._fix_short_roster(63108,1,"[226, 232, 234, 230]",[236],"miss3")
    #

    #
