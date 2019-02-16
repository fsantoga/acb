import re, logging
from pyquery import PyQuery as pq
from collections import defaultdict
from src.utils import fill_dict, replace_nth_ocurrence
from models.basemodel import BaseModel
from models.game import Game
from models.team import Team
from models.actor import Actor
from peewee import (PrimaryKeyField, TextField, IntegerField,
                    ForeignKeyField, BooleanField,)


class Participant(BaseModel):
    """
    Class representing a Participant.

    A participant is a player, actor or referee that participates in a certain game.
    """
    id = PrimaryKeyField()
    game = ForeignKeyField(Game, related_name='participants', index=True)
    team = ForeignKeyField(Team, index=True, null=True)
    actor = ForeignKeyField(Actor, related_name='participations', index=True, null=True)
    display_name = TextField(null=True)
    number = IntegerField(null=True)
    is_coach = BooleanField(null=True)
    is_starter = BooleanField(null=True)
    minutes = IntegerField(null=True)
    point = IntegerField(null=True)
    t2_attempt = IntegerField(null=True)
    t2 = IntegerField(null=True)
    t3_attempt = IntegerField(null=True)
    t3 = IntegerField(null=True)
    t1_attempt = IntegerField(null=True)
    t1 = IntegerField(null=True)
    defensive_reb = IntegerField(null=True)
    offensive_reb = IntegerField(null=True)
    assist = IntegerField(null=True)
    steal = IntegerField(null=True)
    turnover = IntegerField(null=True)
    counterattack = IntegerField(null=True)
    block = IntegerField(null=True)
    received_block = IntegerField(null=True)
    dunk = IntegerField(null=True)
    fault = IntegerField(null=True)
    received_fault = IntegerField(null=True)
    plus_minus = IntegerField(null=True)
    efficiency = IntegerField(null=True)

    @staticmethod
    def create_instances(raw_game, game):
        """
        Extract all the information regarding a participant from a game.

        :param raw_game: string
        :param game: Game instance
        """
        Participant._create_players_and_coaches(raw_game, game)

    @staticmethod
    def _fix_acbid(actor_name, actor_acbid,is_coach):
        """
        Modify the acbid of an actor.

        :param actor_name: String
        :param acbid: String
        """
        try:
            actor = Actor.get(Actor.display_name == actor_name)
            actor.actor_acbid = actor_acbid
            actor.is_coach=is_coach
            actor.save()

        except Exception as e:
            actor = Actor()
            actor.actor_acbid = actor_acbid
            actor.display_name = actor_name
            actor.is_coach=is_coach
            actor.save()

            #print(e)
            #logging.info("The actor {}, cannot be inserted into the database".format(actor_name))
            #pass

    @staticmethod
    def _fix_participations(actor_name, actual_acbid, wrong_acbid):
        """
        In a few cases, acb has created two different actors for the same player. This method corrects this mistake,
        by modifying the actor id in the games of the wrong actor.

        :param actor_name: String
        :param actual_acbid: String
        :param wrong_acbid: String
        :return:
        """
        try:
            actor = Actor.get((Actor.display_name == actor_name) & (Actor.actor_acbid == actual_acbid))
        except Exception as e:
            #print(e)
            logging.info("The participant {}, cannot be inserted into the database".format(actor_name))
            pass
        try:
            wrong_actor = Actor.get((Actor.display_name == actor_name) & (Actor.actor_acbid == wrong_acbid))

            for participation in wrong_actor.participations:
                participation.actor = actor
                participation.save()
            wrong_actor.delete_instance()  # delete the wrong instance.
        except Actor.DoesNotExist:
            pass

    @staticmethod
    def _fix_coaches_participations(actor_name,actor_acbid,team_id):
        try:
            wrong_participant = Participant.get((Participant.display_name == "") & (Participant.team == team_id) & (Participant.is_coach==1))
            actor_id = Actor.get((Actor.display_name == actor_name) & (Actor.actor_acbid == actor_acbid)).id

            wrong_participant.display_name = actor_name
            wrong_participant.actor_id = actor_id
            wrong_participant.save()

        except Participant.DoesNotExist:
            pass

    @staticmethod
    def _fix_players_participations(number,team_id):
        try:
            wrong_participant = Participant.get((Participant.display_name == "") & (Participant.team == team_id) & (Participant.is_coach==0) & (Participant.number == number))
            wrong_participant.delete_instance()

        except Participant.DoesNotExist:
            pass

    @staticmethod
    def fix_participants():
        Participant._fix_acbid('G. Sharabidze', 'Y9G',0)
        Participant._fix_acbid('S. Gacic', '801',0)
        Participant._fix_acbid('M. Milisavljevic', 'D08',0)
        Participant._fix_acbid('L. Marquel', 'A09',0)
        Participant._fix_acbid('I. Navarro', 'A09',1)

        Participant._fix_acbid('J. Espil', 'AYP',0)
        Participant._fix_acbid('J. Ponsarnau', 'AYP',1)

        Participant._fix_acbid('R. Aldrey', 'AET',0)
        Participant._fix_acbid('J. Berrocal', 'AET',1)

        Participant._fix_acbid('D. Allaway', 'AYQ',0)
        Participant._fix_acbid('V. García', 'AYQ',1)

        Participant._fix_acbid('M. Janning', '55A',0)
        Participant._fix_acbid('D. Epifanio', '55A',1)

        Participant._fix_acbid('F. Laviña', 'A0R',0)
        Participant._fix_acbid('M. Justo', 'A0R',1)

        Participant._fix_participations('M. Esteban', '2CH','476')
        Participant._fix_participations('W. Tavares', 'T2Z', 'SHP')
        Participant._fix_participations('M. Stobart', 'B7P', 'FII')
        Participant._fix_participations('J. Olaizola', 'T86', '162')
        Participant._fix_participations('A. Izquierdo', '773', 'YHK')

        Participant._fix_coaches_participations("J. Ponsarnau",'AYP',18)
        Participant._fix_coaches_participations('V. García', 'AYQ',17)
        Participant._fix_coaches_participations('V. García', 'AYQ',17)
        Participant._fix_coaches_participations('V. García', 'AYQ',17)

        Participant._fix_players_participations(17,2)
        Participant._fix_players_participations(0,17)

    @staticmethod
    def _create_players_and_coaches(raw_game, game):
        """
        Extract and create the information about players and coaches.

        :param raw_game: String
        :param game: Game object
        :return: List of Participant objects and list of Actor objects.
        """
        estadisticas_tag = '.estadisticasnew' if re.search(r'<table class="estadisticasnew"',
                                                           raw_game) else '.estadisticas'
        doc = pq(raw_game)
        info_players_data = doc(estadisticas_tag).eq(1)

        """
        We make sure we only retrieve stats that are in the header. One clear example can be found when the
        estadisticas_tag is 'estadisticas' since it hasn't got the +/- stat.
        """
        header_text = info_players_data('tr').eq(1)
        header = []
        for index in header_text('td').items():
            header.append(index.text())

        """
        However, the acb ids of the stats are not unique and some of them are repeteated.
        We have three times a 'C' and two times a 'F'. We manually modify these ids.
        """
        # The first C is counterattack, the second C is received_block and the third received_fault.
        header = replace_nth_ocurrence(header, 3, "C", "FPC")
        header = replace_nth_ocurrence(header, 2, "C", "TAPC")
        # The first F is block and the second F is  fault.
        header = replace_nth_ocurrence(header, 2, "F", "FPF")
        header = replace_nth_ocurrence(header, 1, "F", "TAPF")

        """
        We create the correspondance between the acb ids and the attributes in our database
        """
        header_to_db = {'D': 'number', 'Nombre': "display_name", 'Min': 'minutes', 'P': 'point', 'T2': 't2',
                        'T3': 't3', 'T1': 't1', 'REBD': 'defensive_reb', 'REBO': 'offensive_reb', 'A': 'assist',
                        'BR': 'steal', 'BP': 'turnover', 'C': 'counterattack', 'TAPF': 'block',
                        'TAPC': 'received_block', 'M': 'dunk', 'FPF': 'fault', 'FPC': 'received_fault',
                        '+/-': 'plus_minus', 'V': 'efficiency'}

        """
        Let us remove the database attributes that are not included in the header.
        """
        # Preventing from missing stats
        for key, match in list(header_to_db.items()):
            if key not in header:
                header_to_db.pop(key)

        """
        We add extra attributes that are not inferred directly from the stats, but from the context.
        """
        header_to_db.update({"is_coach": "is_coach",
                             "is_starter": "is_starter",
                             "game": "game",
                             "team": "team",
                             "actor": "actor",
                             "t1_attempt": "t1_attempt",
                             "t2_attempt": "t2_attempt",
                             "t3_attempt": "t3_attempt",
                             "defensive_reb": "defensive_reb",
                             "offensive_reb": "offensive_reb"})

        """
        We create a dictionary that contains, for each of the teams, and for each of the players, and for each of the stats
        the value of such stat for such player of such team.

        > stats[team][player][stat]

        where 'team' is the name of the team, 'player' is the number of the player and 'stat' is the acb stat id.
        """
        acb_error_player = None
        stats = defaultdict(dict)
        current_team = None
        score_flag = 0
        for tr in info_players_data('tr').items():  # iterate over each row
            if tr('.estverde'):  # header
                if tr.eq(0)('.estverdel'):  # team information
                    current_team = 0 if current_team is None else 1  # first team home team
                    stats[current_team] = defaultdict(dict)
                else:  # omit indexes
                    pass
            else:  # players, equipo, and coach.
                number = None
                for cont, td in enumerate(tr('td').items()):  # iterate over each cell (stat)

                    if td.text() == "5f":
                        break

                    elif td.text() == 'Total' or number == 'Total':
                        number = 'Total'
                        if score_flag < 2:
                            score_flag += 1
                            continue
                        elif score_flag == 2:
                            score_flag += 1
                            try:
                                game.score_home = int(td.text()) if current_team == 0 else game.score_home
                            except Exception as e:
                                print(e)
                                pass
                            try:
                                game.score_away = int(td.text()) if current_team == 1 else game.score_away
                            except Exception as e:
                                print(e)
                                pass
                            game.save()
                            continue
                        else:
                            score_flag = 0
                            break

                    elif cont == 0:  # first cell number of the player
                        number = td.text() if td.text() else 'Equipo'
                        #if number == 'Equipo': #¿Queremos que las stats de equipo en un partido se metan en participantes????
                        #    break
                        if number in stats[current_team]:  # preventing from errors with the number.
                            wrong_pages_first = ['55313', '54017', '54026', '61072', '61076', '61107','62177']  # if the good one is the first.
                            wrong_pages_second = ['53154', '61218','62177']  # if the good one is the second.
                            if game.game_acbid in wrong_pages_first:  # acb error... >:(
                                pass
                            elif game.game_acbid in wrong_pages_second:
                                stats[current_team][number] = acb_error_player
                                break
                            else:  # sometimes th acb has some duplicated players (error).
                                continue
                                #raise ValueError('Number {} does already exist in game {}!'.format(number, game.game_acbid))

                        else:
                            # Create the dict with default attributes.
                            stats[current_team][number] = fill_dict(header_to_db.values())
                            stats[current_team][number]['is_starter'] = 1 if td('.gristit') else 0
                            stats[current_team][number]['game'] = game
                            stats[current_team][number]['team'] = game.team_home_id if current_team == 0 else game.team_away_id

                    elif cont == 1 and td('a'):  # second cell player id
                        href_attribute = td('a').attr('href').split("=")  # the acb id is in the href attribute.
                        stats[current_team][number]['id'] = href_attribute[-1]

                        is_coach = re.search(r'entrenador', href_attribute[0])
                        stats[current_team][number]['is_coach'] = 1 if is_coach else 0
                        stats[current_team][number]['number'] = None if is_coach else int(number)


                        display_name = td.text()
                        #if display_name=="":
                        #    stats=None
                        #    pass
                        #else:
                        if ',' in display_name:
                            try:
                                last_name, first_name = list(map(lambda x: x.strip(), td.text().split(",")))
                                new_display_name = str(first_name)[0] + '. ' + last_name
                                stats[current_team][number]['display_name'] = new_display_name
                            except: # E.g Milisavljevic,                                new_display_name=last_name
                                stats[current_team][number]['display_name'] = new_display_name
                        else:  # E.g. San Emeterio
                            stats[current_team][number]['display_name'] = display_name



                    elif '%' in header[cont]:  # discard percentages.
                        continue

                    elif '/' in td.text():  # T1, T2 or T3 in format success/attempts.
                        success, attempts = td.text().split("/")
                        try:
                            stats[current_team][number][header_to_db[header[cont]]] = int(success)
                        except Exception as e:
                            print(e)
                            pass
                        try:
                            stats[current_team][number][header_to_db[header[cont]] + "_attempt"] = int(attempts)
                        except Exception as e:
                            print(e)
                            pass

                    elif '+' in td.text():  # defensive and offensive rebounds in format D+O
                        defensive, offensive = td.text().split("+")
                        try:
                            stats[current_team][number]["defensive_reb"] = int(defensive)
                        except Exception as e:
                            print(e)
                            pass
                        try:
                            stats[current_team][number]["offensive_reb"] = int(offensive)
                        except Exception as e:
                            print(e)
                            pass

                    elif ':' in td.text():  # minutes in format minutes:seconds
                        minutes, seconds = td.text().split(":")
                        stats[current_team][number]["minutes"] = int(minutes) * 60 + int(seconds)

                    else:
                        if header[cont] in header_to_db:  # only add useful stats.
                            try:
                                stats[current_team][number][header_to_db[header[cont]]] = int(
                                    td.text()) if td.text() else 0
                            except:
                                stats[current_team][number][header_to_db[header[cont]]] = td.text()

                    acb_error_player = stats[current_team][number]
        """
        We now insert the participants of the game in the database.
        Therefore, we need first to get or create the actors in the database.

        We consider an actor as a player or a coach. We don't have information about referees so we don't include
        them here.
        """
        to_insert_many_participants = []
        actors = []
        for team, team_dict in stats.items():
            for player, player_stats in team_dict.items():
                try:
                    if stats[team][player]['id']=="" or stats[team][player]['display_name']=="":
                        #del stats[team][player]
                        stats[team][player].pop('id')
                        pass
                    actor = Actor.get_or_create(actor_acbid=stats[team][player]['id'],display_name=stats[team][player]['display_name'])
                    if actor[1]:
                        actor[0].display_name = stats[team][player]['display_name']
                        actor[0].is_coach = stats[team][player]['is_coach']
                        actor[0].save()
                        actors.append(actor)
                    stats[team][player]['actor'] = actor[0]
                    stats[team][player].pop('id')
                except KeyError:
                    pass
                to_insert_many_participants.append(stats[team][player])

        participants = Participant.insert_many(to_insert_many_participants)
        participants.execute()
