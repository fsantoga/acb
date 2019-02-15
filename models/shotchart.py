import os.path, re, difflib, logging
from src.download import get_page,save_content,sanity_check_shotchart
from models.basemodel import BaseModel, db
from models.team import Team
from models.actor import Actor
from models.game import Game
from models.participant import Participant
from src.utils import convert_time, create_driver
from peewee import (PrimaryKeyField, ForeignKeyField, CharField, TextField, IntegerField,DoubleField)
import time
from src.utils import get_current_season
import math

shot_type_dict = {
    '2PT': '2PT',
    '3PT': '3PT',
    '2PT bandeja': '2PT',
    '2PT palmeo': '2PT',
    '2PT tiro': '2PT',
    '2PT Alley oop': '2PT',
    '2PT Alley-oop': '2PT',
    'Mate': '2PT',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT': '2PT',
    'BASKETBALL_ACTION_2PT_HOOKSHOT': '2PT',
    'BASKETBALL_ACTION_3PT_JUMPSHOT': '3PT',
}

extra_shot_type_dict = {
    '2PT bandeja': 'layup',
    '2PT palmeo': 'tip',
    '2PT tiro': 'jumpshot',
    '2PT Alley oop': 'alley-oop',
    '2PT Alley-oop': 'alley-oop',
    'Mate': 'dunk',
    'BASKETBALL_ACTION_2PT_STEPBACKJUMPSHOT': 'stepback',
    'BASKETBALL_ACTION_2PT_HOOKSHOT': 'hookshot',
}

class Shotchart(BaseModel):
    id = PrimaryKeyField()
    shotchart_game_acbid = IntegerField(index=True)
    game_acbid = IntegerField(index=True)
    team_id = ForeignKeyField(Team, index=False, null=True)
    scored = IntegerField(null=True)
    period = CharField(null=True)
    shot = CharField(null=True)
    shot_type = CharField(null=True)
    jersey = IntegerField(null=True)
    actor_id = ForeignKeyField(Actor, index=False, null=True)
    botton_px = DoubleField(null=True)
    left_px = DoubleField(null=True)
    botton_px_adjust = DoubleField(null=True)
    left_px_adjust = DoubleField(null=True)
    left_m_adjust = DoubleField(null=True)
    botton_m_adjust = DoubleField(null=True)
    distance = DoubleField(null=True)


    @staticmethod
    def save_shotchart(season, driver_path, logging_level=logging.INFO):
        """
        Method for saving locally the games of a season.
        :param season: int
        :param logging_level: logging object
        :return:
        """

        logging.basicConfig(level=logging_level)
        logger = logging.getLogger(__name__)

        logger.info('Taking all the ids for the shotchart-games...')

        if season.season == get_current_season():
            fibalivestats_ids = season.get_current_game_events_ids()
        else:
            fibalivestats_ids = season.get_game_events_ids()

        logger.info('Starting the download of shotchart...')

        driver = create_driver(driver_path)
        n_checkpoints = 10
        checkpoints = [int(i * float(len(fibalivestats_ids)) / n_checkpoints) for i in range(n_checkpoints + 1)]
        for i, (fls_id, game_acbid) in enumerate(fibalivestats_ids.items()):
            filename = os.path.join(season.SHOTCHART_PATH, str(game_acbid)+"-"+str(fls_id) + ".html")
            shotchartURL="http://www.fibalivestats.com/u/ACBS/{}/sc.html".format(fls_id)
            if not os.path.isfile(filename):
                try:
                    driver.get(shotchartURL)
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
    def sanity_check_shotchart(driver_path,season, logging_level=logging.INFO):
        sanity_check_shotchart(driver_path,season.SHOTCHART_PATH, logging_level)

    @staticmethod
    def scrap_and_insert(shotchart_game_acbid, game_acbid, shotchart, team_home_id, team_away_id):
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)

        periods = set()
        actions = {}
        cont = 1
        home_score = away_score = 0
        first_shot=True
        home_attack_left=0

        for elem in list(shotchart('span').items()):

            query_actor_id=None
            scored=None
            period=None
            botton_px=None
            left_px=None
            shot=None
            shot_type_final=None
            botton_px_adjust=None
            left_px_adjust=None

            if elem.attr['class']:
                tag = elem.attr['class']
                list_tags=tag.split(" ")
                shot_score=list_tags[1]
                shot_score_adjust=shot_score.split("_")[0]

                if shot_score=="black_missed" or shot_score=="white_missed":
                    scored=0
                elif shot_score=="black_made" or shot_score=="white_made":
                    scored=1

                period=list_tags[2]

                if period=="sc_per1":
                    period=1
                elif period=="sc_per2":
                    period=2
                elif period=="sc_per3":
                    period=3
                elif period=="sc_per4":
                    period=4
                elif period=="sc_perot":
                    period="OT"

                team=list_tags[4]

                if team=="sc_tn2":
                    team_id=team_away_id
                else:
                    team_id=team_home_id

            if elem.attr['style']:

                tag = elem.attr['style']
                list_tags=tag.split(" ")
                botton_px=list_tags[1]
                botton_px=float(botton_px.split("%")[0])
                left_px=list_tags[3]
                left_px=float(left_px.split("%")[0])

                if first_shot:
                    if left_px < 50.0:
                        if team == "sc_tn1":
                            home_attack_left = 1
                        else:
                            home_attack_left = 0
                    else:
                        if team == "sc_tn1":
                            home_attack_left = 0
                        else:
                            home_attack_left = 1

                    first_shot = False

                if shot_score_adjust=="white" and home_attack_left==1:
                    if period in [1,2]:
                        left_px_adjust=left_px
                        botton_px_adjust=botton_px
                    else:
                        left_px_adjust=100.0-left_px
                        botton_px_adjust=100.0-botton_px

                elif shot_score_adjust=="white" and home_attack_left==0:
                    if period in [1,2]:
                        left_px_adjust=100.0-left_px
                        botton_px_adjust=100.0-botton_px
                    else:
                        left_px_adjust=left_px
                        botton_px_adjust=botton_px

                elif shot_score_adjust == "black" and home_attack_left == 1:
                    if period in [1, 2]:
                        left_px_adjust = 100.0-left_px
                        botton_px_adjust = 100.0-botton_px
                    else:
                        left_px_adjust = left_px
                        botton_px_adjust = botton_px

                elif shot_score_adjust == "black" and home_attack_left == 0:
                    if period in [1, 2]:
                        left_px_adjust = left_px
                        botton_px_adjust = botton_px
                    else:
                        left_px_adjust = 100.0-left_px
                        botton_px_adjust = 100.0-botton_px

                if elem.attr['title']:
                    tag = elem.attr['title']
                    if tag.startswith(","):
                        tag = tag.split(",")
                        list_tags = tag.remove(tag[0])
                        jersey = tag[0].strip()
                        display_name = tag[1].strip()
                        shot_txt = tag[2].strip()
                    else:
                        list_tags = tag.split(",")
                        jersey = list_tags[0]
                        display_name = list_tags[1].strip()
                        shot_txt = list_tags[2].strip()

                game_id = Game.get(Game.game_acbid == game_acbid).id

                try:  ## In case the name of the actor is exactly the same as one stated in our database this game
                    query_actor_id = Participant.get(
                        (Participant.game == game_id) & (Participant.display_name % display_name)).actor

                except Participant.DoesNotExist:  ## In case there is not an exact correspondance within our database, let's find the closest match.
                    query = Participant.select(Participant.actor, Participant.display_name).where((Participant.game == game_id) & (Participant.actor.is_null(False)) & (Participant.team == team_id))
                    actors_names_ids = dict()
                    for q in query:
                        actors_names_ids[q.display_name] = q.actor.id

                    most_likely_actor = difflib.get_close_matches(display_name, actors_names_ids.keys(), 1, 0.4)[0]
                    query_actor_id = Actor.get(Actor.id == actors_names_ids[most_likely_actor]).id
                    logger.info('Actor {} has been matched to: {}'.format(display_name, most_likely_actor))


                #Fixing ACB errors
                if shot=="2PT" and left_px_adjust > 50.0:
                    left_px_adjust = 100.0 - left_px
                    botton_px_adjust = 100.0 - botton_px

                left_m_adjust = (left_px_adjust * 28) / 100
                botton_m_adjust = (botton_px_adjust * 15) / 100

                center_left = 1.575
                center_botton=7.5

                distance = math.sqrt((left_m_adjust - center_left) ** 2 + (botton_m_adjust - center_botton) ** 2)

                actions[cont] = {"shotchart_game_acbid": shotchart_game_acbid,
                                 "game_acbid": game_acbid,
                                 "team_id": team_id,
                                 "actor_id": query_actor_id,
                                 "jersey": jersey,
                                 "scored": scored,
                                 "period": period,
                                 "botton_px": botton_px,
                                 "left_px": left_px,
                                 "botton_px_adjust": botton_px_adjust,
                                 "left_px_adjust": left_px_adjust,
                                 "botton_m_adjust": botton_m_adjust,
                                 "left_m_adjust": left_m_adjust,
                                 "distance": distance,
                                 "shot": shot_type_dict[shot_txt],
                                 "shot_type": extra_shot_type_dict.setdefault(shot_txt, None)}
                cont += 1

        with db.atomic():
            for event in actions.values():
                Shotchart.create(**event)

