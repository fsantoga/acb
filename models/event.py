import os.path, re, datetime, difflib, logging
from src.download import open_or_download, sanity_check, get_page,save_content,sanity_check_events
from models.basemodel import BaseModel, db
from src.utils import convert_time, create_driver
from peewee import (PrimaryKeyField, TextField, IntegerField,
                    DateTimeField, ForeignKeyField, BooleanField)
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import time


legend_dict = {
    'Asistencia': 'assist',
    'Tapón': 'block',
    'Recuperación': 'steal',
    'Pérdida': 'turnover',
    'Pérdida en el manejo del balón': 'turnover',
    'Pérdida por campo atrás': 'turnover',
    'Pérdida por 3 segundos': 'turnover',
    'Pérdida por 5 segundos': 'turnover',
    'Pérdida por falta en ataque': 'turnover',
    'Pérdida por fuera de banda': 'turnover',
    'Pérdida por mal pase': 'turnover',
    'Pérdida por pasos': 'turnover',
    'Pérdida por interferencia en ataque': 'turnover',
    'Pérdida por 24 segundos': 'turnover',
    'Pérdida por 8 segundos': 'turnover',
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
    '3PT convertido': 'made3',
    '3PT fallado': 'miss3',
    'Salto ganado': 'tipoff_won',
    'Salto perdido': 'tipoff_lost',
    'COMIENZA EL PARTIDO': 'game_start',
    'PARTIDO FINALIZADO': 'game_end',
    'INICIO PERIODO': 'quarter_start',
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
}

class Event(BaseModel):
    id = PrimaryKeyField()
    event_id = IntegerField()
    game_id = IntegerField(index=True)
    team_id = TextField(null=True)
    legend = TextField(null=True)
    extra_info = TextField(null=True)
    elapsed_time = IntegerField(null=True)
    display_name = TextField(null=True)
    jersey = IntegerField(null=True)
    home_score = IntegerField(null=True)
    away_score = IntegerField(null=True)

    @staticmethod
    def save_events(season, driver_path, logging_level=logging.INFO):
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

        logger.info('Taking all the ids for the events-games...')

        fibalivestats_ids = {}
        for i in range(from_journey, to_journey + 1):
            url = "http://jv.acb.com/historico.php?jornada={}&cod_competicion=LACB&cod_edicion={}".format(i,season.season_id)
            content = get_page(url)

            fls_ids = re.findall(r'<div class="partido borde_azul" id="partido-([0-9]+)">', content, re.DOTALL)
            game_ids = re.findall(r'"http://www.acb.com/fichas/LACB([0-9]+).php', content, re.DOTALL)
            fibalivestats_ids.update(dict(zip(fls_ids, game_ids)))

        logger.info('Starting the download of events...')

        driver = create_driver(driver_path)
        n_checkpoints = 10
        checkpoints = [int(i * float(len(fibalivestats_ids)) / n_checkpoints) for i in range(n_checkpoints + 1)]
        for i, (fls_id, game_id) in enumerate(fibalivestats_ids.items()):
            filename = os.path.join(season.EVENTS_PATH, str(game_id)+"-"+str(fls_id) + ".html")
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
        logger.info('Download finished!)')

    @staticmethod
    def sanity_check_events(driver_path,season, logging_level=logging.INFO):
        sanity_check_events(driver_path,season.EVENTS_PATH, logging_level)

    @staticmethod
    def scrap_and_insert(game_id, playbyplay, team_code_1, team_code_2):
        periods = set()
        actions = {}
        cont = 1
        home_score = away_score = 0
        for elem in reversed(list(playbyplay('div').items())):
            if elem.attr['class'] and elem.attr['class'].startswith("pbpa"):

                tag = elem.attr['class']
                team_id = team_code_1 if "pbpt1" in tag else team_code_2 if "pbpt2" in tag else None

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

                except:  # Cells without player associated (e.g. timeouts and missing info)
                    legend = elem('.pbp-action').text() if elem('.pbp-action').text() != '' else \
                    elem.text().split("\n")[0]
                    time = elem.attr['id']
                    period = "P" + re.search(r'per_[a-z]?([a-z]?[0-9]+)', tag).groups()[0]
                    display_name = None
                    jersey = -1

                elapsed_time = convert_time(time, period[1:])
                actions[cont] = {"event_id": cont,
                                 "game_id": game_id,
                                 "team_id": team_id,
                                 "legend": legend_dict[legend],
                                 "extra_info": extra_legend_dict.setdefault(legend, None),
                                 "elapsed_time": elapsed_time,
                                 "display_name": display_name,
                                 "jersey": jersey,
                                 "home_score": home_score,
                                 "away_score": away_score}
                cont += 1

        with db.atomic():
            for event in actions.values():
                Event.create(**event)
