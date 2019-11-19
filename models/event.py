import os.path, re, difflib, logging
from src.download import get_page,save_content,sanity_check_events
from models.basemodel import BaseModel, db
from models.team import Team
from models.actor import Actor
from src.utils import convert_time, create_driver
from peewee import (PrimaryKeyField, ForeignKeyField, CharField, TextField, IntegerField)
import time
from src.utils import get_current_season
import ast
import mysql.connector as sql
import pandas as pd


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
    '2PT palmeo convertido': 'made2',
    '2PT palmeo fallado': 'miss2',
    '2PT tiro convertido': 'made2',
    'Mate convertido': 'made2',
    '2PT tiro fallado': 'miss2',
    '2PT Alley oop convertido': 'made2',
    '2PT Alley-oop convertido': 'made2',
    '3PT convertido': 'made3',
    '3PT fallado': 'miss3',
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
    '2PT palmeo convertido': 'tip',
    '2PT palmeo fallado': 'tip',
    '2PT tiro convertido': 'jumpshot',
    '2PT Alley oop convertido': 'alleyhoop',
    '2PT Alley-oop convertido': 'alleyhoop',
    'Mate convertido': 'dunk',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT convertido': 'stepback',
    'BASKETBALL_ACTION_2PT_HOOKSHOT convertido': 'hookshot',
    'BASKETBALL_ACTION_2PT_HOOKSHOT fallado': 'hookshot',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT fallado': 'stepback',
}

play_events_dict={
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
    'Salto balón retenido': 'salto',
    'Falta antideportiva': 'foul',
    'Falta en ataque': 'foul',
    'Falta personal': 'foul',
    'Falta recibida': 'foul_rv',
    'Falta técnica': 'foul',
    'Falta descalificante': 'foul',
    'Técnica al banquillo': 'foul',
    'Técnica al entrenador': 'foul',
    'Rebote ofensivo': 'reb_off',
    'Rebote defensivo': 'reb_def',
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
    '2PT palmeo convertido': 'made2',
    '2PT palmeo fallado': 'miss2',
    '2PT tiro convertido': 'made2',
    'Mate convertido': 'made2',
    '2PT tiro fallado': 'miss2',
    '2PT Alley oop convertido': 'made2',
    '2PT Alley-oop convertido': 'made2',
    '3PT convertido': 'made3',
    '3PT fallado': 'miss3',
    'Salto ganado': 'tipoff_won',
    'Salto perdido': 'tipoff_lost',
    'jumpball.unclearposs': 'jumpball_unclearposs',
    'BASKETBALL_ACTION_3PT_JUMPSHOT convertido': 'made3',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT convertido': 'made2',
    'BASKETBALL_ACTION_2PT_HOOKSHOT convertido': 'made2',
    'BASKETBALL_ACTION_3PT_JUMPSHOT fallado': 'miss3',
    'BASKETBALL_ACTION_2PT_HOOKSHOT fallado': 'miss2',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT fallado': 'miss2',
}

class Event(BaseModel):
    id = PrimaryKeyField()
    events_game_acbid = IntegerField(index=True)
    game_acbid = IntegerField(index=True)
    team_id = ForeignKeyField(Team, index=False, null=True)
    legend = TextField(null=True)
    extra_info = TextField(null=True)
    elapsed_time = IntegerField(null=True)
    jersey = IntegerField(null=True)
    actor_id = ForeignKeyField(Actor, index=False, null=True)
    home_score = IntegerField(null=True)
    away_score = IntegerField(null=True)
    roster_home = CharField(null=True)
    roster_away = CharField(null=True)

    @staticmethod
    def save_events(season, driver_path, logging_level=logging.INFO):
        """
        Method for saving locally the games of a season.
        :param season: int
        :param logging_level: logging object
        :return:
        """

        logging.basicConfig(level=logging_level)
        logger = logging.getLogger(__name__)

        logger.info('Taking all the ids for the events-games...')

        if season.season == get_current_season():
            fibalivestats_ids = season.get_current_game_events_ids()
        else:
            fibalivestats_ids = season.get_game_events_ids()

        logger.info('Starting the download of events...')

        driver = create_driver(driver_path)
        n_checkpoints = 10
        checkpoints = [int(i * float(len(fibalivestats_ids)) / n_checkpoints) for i in range(n_checkpoints + 1)]
        for i, (fls_id, game_acbid) in enumerate(fibalivestats_ids.items()):
            filename = os.path.join(season.EVENTS_PATH, str(game_acbid)+"-"+str(fls_id) + ".html")
            eventURL="http://www.fibalivestats.com/u/ACBS/{}/pbp.html".format(fls_id)
            if not os.path.isfile(filename):
                try:
                    driver.get(eventURL)
                    time.sleep(1)
                    html = driver.page_source
                    save_content(filename,html)
                except Exception as e:
                    logger.info(str(e) + ' when trying to retrieve ' + filename)
                    pass

            # Debugging
            if i-1 in checkpoints:
                logger.info('{}% already downloaded'.format(round(float(i-1) / len(fibalivestats_ids) * 100)))

        driver.close()
        logger.info('Download finished!)\n')

    @staticmethod
    def sanity_check_events(driver_path,season, logging_level=logging.INFO):
        sanity_check_events(driver_path,season.EVENTS_PATH, logging_level)

    @staticmethod
    def save_events_copa(season, driver_path, logging_level=logging.INFO):
        """
        Method for saving locally the games of a season.
        :param season: int
        :param logging_level: logging object
        :return:
        """

        logging.basicConfig(level=logging_level)
        logger = logging.getLogger(__name__)

        logger.info('Taking all the ids for the events-games...')

        if season.season == get_current_season():
            fibalivestats_ids = season.get_current_game_events_ids_copa()
        else:
            fibalivestats_ids = season.get_game_events_ids_copa()

        logger.info('Starting the download of events...')

        driver = create_driver(driver_path)
        n_checkpoints = 10
        checkpoints = [int(i * float(len(fibalivestats_ids)) / n_checkpoints) for i in range(n_checkpoints + 1)]
        for i, (fls_id, game_acbid) in enumerate(fibalivestats_ids.items()):
            filename = os.path.join(season.EVENTS_PATH_COPA, str(game_acbid)+"-"+str(fls_id) + ".html")
            eventURL="http://www.fibalivestats.com/u/ACBS/{}/pbp.html".format(fls_id)
            if not os.path.isfile(filename):
                try:
                    driver.get(eventURL)
                    time.sleep(1)
                    html = driver.page_source
                    save_content(filename,html)
                except Exception as e:
                    logger.info(str(e) + ' when trying to retrieve ' + filename)
                    pass

            # Debugging
            if i-1 in checkpoints:
                logger.info('{}% already downloaded'.format(round(float(i-1) / len(fibalivestats_ids) * 100)))

        driver.close()
        logger.info('Download finished!)\n')

    @staticmethod
    def sanity_check_events_copa(driver_path,season, logging_level=logging.INFO):
        sanity_check_events(driver_path,season.EVENTS_PATH_COPA, logging_level)

    @staticmethod
    def _fix_short_roster(game_acbid, roster_home_or_away, roster, list_include_actor, legend):
        if roster_home_or_away==0:
            try:
                wrong_roster = Event.get((Event.game_acbid==game_acbid) & (Event.roster_home==roster) & (Event.legend==legend))
                roster_list = ast.literal_eval(roster)
                for elem in list_include_actor:
                    roster_list.append(elem)

                wrong_roster.roster_home = roster_list
                wrong_roster.save()

            except Event.DoesNotExist:
                pass

        elif roster_home_or_away==1:
            try:
                wrong_roster = Event.get((Event.game_acbid==game_acbid) & (Event.roster_away==roster) & (Event.legend==legend))
                roster_list = ast.literal_eval(roster)
                for elem in list_include_actor:
                    roster_list.append(elem)

                wrong_roster.roster_away = roster_list
                wrong_roster.save()

            except Event.DoesNotExist:
                pass

    """
    @staticmethod
    def _fix_long_roster(game_acbid, team_id,roster_length,list_include_actor):
        try:
            wrong_participant = Participant.get(
                (Participant.display_name == "") & (Participant.team == team_id) & (Participant.is_coach == 0) & (
                Participant.number == number))
            wrong_participant.delete_instance()

        except Participant.DoesNotExist:
            pass
    """

    @staticmethod
    def _check_rosters():
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info('Starting the roster checking...')

        query = Event.select().dicts()

        for row in query:
            if row['legend'] in play_events_dict.values():
                roster_home_list = ast.literal_eval(row['roster_home'])
                roster_away_list = ast.literal_eval(row['roster_away'])

                if len(roster_home_list) != 5:
                    logger.warning(
                        'Game: {} ({}). Roster home list length ({}) error: {} for team: {} and event: {}'.format(
                            row['game_acbid'], row['events_game_acbid'], len(roster_home_list), row['roster_home'], row['team_id'],
                            row['legend']))
                if len(roster_away_list) != 5:
                    logger.warning(
                        'Game: {} ({}). Roster away list length ({}) error: {} for team: {} and event: {}'.format(
                            row['game_acbid'], row['events_game_acbid'], len(roster_away_list), row['roster_away'], row['team_id'],
                            row['legend']))

    @staticmethod
    def fix_rosters():
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        logger.info('Starting the roster fixing...')

        Event._fix_short_roster(63018,0,"[24, 18, 25, 15]",[10],"turnover")
        Event._fix_short_roster(63018,0,"[24, 18, 25, 15]",[10],"steal")

        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"steal")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss1")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"block")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"assist")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"steal")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_off")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"steal")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_off")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made1")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[62, 63, 64, 55]",[53],"turnover")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"made2")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"assist")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"foul")
        Event._fix_short_roster(63016,1,"[62, 55, 253, 57]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"reb_def")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"made2")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"assist")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"miss1")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"miss1")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul")
        Event._fix_short_roster(63016,1,"[55, 253, 57, 59]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"turnover")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made2")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"miss3")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"reb_off")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made2")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"miss2")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"reb_off")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made2")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"assist")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"foul")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"foul_rv")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"made1")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"miss1")
        Event._fix_short_roster(63016,1,"[253, 57, 59, 61]",[53],"reb_def")

        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "tipoff_won")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "tipoff_won")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "tipoff_lost")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "tipoff_lost")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "turnover")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "turnover")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "steal")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "steal")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul_rv")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul_rv")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made3")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254],"made2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul_rv")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul_rv")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "turnover")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "turnover")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made3")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "turnover")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "turnover")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "foul_rv")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "foul_rv")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_off")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_off")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "assist")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "assist")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "made2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss2")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "block")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "block")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "reb_off")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "reb_off")
        Event._fix_short_roster(63043, 0, "[]", [286, 212, 216, 218, 254], "miss3")
        Event._fix_short_roster(63043, 1, "[]", [46, 43, 48, 44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[]", [220, 212, 216, 218, 254], "reb_def")
        Event._fix_short_roster(63043, 1, "[]", [41, 43, 49, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul")
        Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul_rv")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul_rv")
        Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "miss1")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "miss1")
        Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "made1")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "made1")
        Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "assist")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "assist")
        Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul")
        Event._fix_short_roster(63043, 0, "[220]", [212, 216, 218, 254], "foul_rv")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul_rv")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss3")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_def")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made3")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "made3")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss2")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_def")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "turnover")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "turnover")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul_rv")
        Event._fix_short_roster(63043, 1, "[41, 49]", [43, 44, 50], "foul_rv")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss2")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_off")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "reb_off")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "made2")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "made2")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "miss3")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "miss3")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "reb_off")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "reb_off")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "foul")
        Event._fix_short_roster(63043, 0, "[220, 223]", [212, 216, 218], "foul_rv")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "foul_rv")
        Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "miss2")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "miss2")
        Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "reb_def")
        Event._fix_short_roster(63043, 1, "[41, 49, 45]", [44, 50], "reb_def")
        Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "miss2")
        Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "miss2")
        Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "reb_off")
        Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "reb_off")
        Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "made2")
        Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "made2")
        Event._fix_short_roster(63043, 0, "[220, 223, 221, 214]", [216], "turnover")
        Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "turnover")
        Event._fix_short_roster(63043, 1, "[41, 49, 45, 47]", [50], "made2")

        Event._fix_short_roster(63086,1,"[177, 184, 180, 182]",[176],"reb_off")

        Event._fix_short_roster(63048,1,"[232, 227, 233, 225]",[229],"miss1")
        Event._fix_short_roster(63048,1,"[232, 227, 233, 225]",[229],"made1")
        Event._fix_short_roster(63048,0,"[43, 51, 45, 41]",[49],"made1")

        Event._fix_short_roster(63160,0,"[128, 121, 117, 119]",[126],"reb_def")

        Event._fix_short_roster(63050,1,"[16, 24, 25, 15]",[14],"miss3")

        Event._fix_short_roster(63123,0,"[14, 171, 24, 25]",[16],"made1")
        Event._fix_short_roster(63123,0,"[14, 171, 24, 25]",[16],"made1")
        Event._fix_short_roster(63123,0,"[14, 171, 24, 25]",[16],"assist")

        Event._fix_short_roster(63031,1,"[254, 214, 221, 222]",[216],"miss3")

        Event._fix_short_roster(63159,0,"[86, 124, 82, 89]",[79],"made1")

        Event._fix_short_roster(63008,0,"[51, 42, 47, 49]",[41],"made1")
        Event._fix_short_roster(63008,0,"[41, 43, 46, 42]",[51],"made1")
        Event._fix_short_roster(63008,0,"[41, 43, 46, 42]",[51],"made1")

        Event._fix_short_roster(63029,1,"[77, 240, 72, 67]",[74],"made1")
        Event._fix_short_roster(63029,1,"[77, 240, 72, 67]",[74],"made1")
        Event._fix_short_roster(63029,1,"[75, 70, 74, 71]",[67],"made1")
        Event._fix_short_roster(63029,1,"[75, 70, 74, 71]",[67],"made1")

        Event._fix_short_roster(63108,1,"[226, 232, 234, 230]",[236],"miss3")

    @staticmethod
    def scrap_and_insert(events_game_acbid, game_acbid, playbyplay, team_home_id, team_away_id, actors_home, actors_away):
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        actions = {}
        cont = 1
        events_with_errors=0
        home_score = away_score = 0

        roster_home=[]
        roster_away=[]

        for elem in reversed(list(playbyplay('div').items())):
            if elem.attr['class'] and elem.attr['class'].startswith("pbpa"):

                tag = elem.attr['class']
                team_id = team_home_id if "pbpt1" in tag else team_away_id if "pbpt2" in tag else None

                try:
                    legend = elem('.pbp-action').text().split(", ")[-1].split("\n")[0]
                    period, marker = elem('.pbp-time').text().split(" ")
                    marker_search = re.search(r'([0-9]{2}:[0-9]{2})([0-9]+)-([0-9]+)', marker)
                    if marker_search:
                        time, home_score, away_score = marker_search.groups()
                    else:
                        time = re.search(r'([0-9]{2}:[0-9]{2})', marker).groups()[0]
                    jersey, display_name, _ = elem('.pbp-action').text().split(", ")
                    jersey = int(jersey)

                    # Matching display_name with actor_id
                    if team_id == team_home_id:
                        actors_names_ids = actors_home
                    elif team_id == team_away_id:
                        actors_names_ids = actors_away
                    else:
                        actors_names_ids = None

                    if display_name in actors_names_ids.keys():
                        query_actor_id = actors_names_ids[display_name]
                    else:
                        most_likely_actor = difflib.get_close_matches(display_name, actors_names_ids.keys(), 1, 0.4)[0]
                        query_actor_id = actors_names_ids[most_likely_actor]
                        logger.info('Actor {} has been matched to: {}'.format(display_name, most_likely_actor))

                except:  # Cells without player associated (e.g. timeouts and missing info)
                    legend = elem('.pbp-action').text() if elem('.pbp-action').text() != '' else \
                    elem.text().split("\n")[0]
                    time = elem.attr['id']
                    period = "P" + re.search(r'per_[a-z]?([a-z]?[0-9]+)', tag).groups()[0]
                    jersey = -1
                    query_actor_id=None

                #roster home
                if "pbpt1" in tag:
                    if legend_dict[legend]=="sub_in":
                        if query_actor_id not in roster_home:
                            roster_home.append(query_actor_id)
                    elif legend_dict[legend]=="sub_out":
                        try:
                            roster_home.remove(query_actor_id)
                        except:
                            logger.warning('Game: {} ({}). Cannot remove actor. Actor {} is not in list {}'.format(game_acbid, events_game_acbid, query_actor_id, roster_home))

                #roster away
                elif "pbpt2" in tag:
                    if legend_dict[legend]=="sub_in":
                        if query_actor_id not in roster_away:
                            roster_away.append(query_actor_id)
                    elif legend_dict[legend]=="sub_out":
                        try:
                            roster_away.remove(query_actor_id)
                        except:
                            logger.warning('Game: {} ({}). Cannot remove actor. Actor {} is not in list {}'.format(game_acbid, events_game_acbid, query_actor_id, roster_away))

                if legend in play_events_dict:
                    if len(roster_home) != 5:
                        events_with_errors+=1
                        logger.warning('Game: {} ({}). Roster home list length ({}) error: {} for team: {} and event: {}'.format(game_acbid,events_game_acbid,len(roster_home),roster_home,team_home_id,legend_dict[legend]))
                    if len(roster_away) != 5:
                        events_with_errors += 1
                        logger.warning('Game: {} ({}). Roster away list length ({}) error: {} for team: {} and event: {}'.format(game_acbid,events_game_acbid,len(roster_away),roster_away,team_away_id,legend_dict[legend]))
                    #if query_actor_id not in roster_home and query_actor_id not in roster_away:
                        #if jersey is not -1:
                        #logger.warning('Game: {} ({}). The actor: {} with jersey: {} is not in the field for event: {}. Roster home {}, Roster away: {}'.format(game_acbid,events_game_acbid,query_actor_id,jersey,legend_dict[legend],roster_home,roster_away))

                elapsed_time = convert_time(time, period[1:])
                actions[cont] = {"events_game_acbid": events_game_acbid,
                                 "game_acbid": game_acbid,
                                 "team_id": team_id,
                                 "actor_id": query_actor_id,
                                 "legend": legend_dict[legend],
                                 "extra_info": extra_legend_dict.setdefault(legend, None),
                                 "elapsed_time": elapsed_time,
                                 "jersey": jersey,
                                 "home_score": home_score,
                                 "away_score": away_score,
                                 "roster_home": str(roster_home),
                                 "roster_away": str(roster_away)}
                cont+=1

        with db.atomic():
            for event in actions.values():
                Event.create(**event)

        return events_with_errors

