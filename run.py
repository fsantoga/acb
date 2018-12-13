import argparse, os, re,glob
from models.basemodel import db, reset_database, delete_records, create_schema
from models.game import Game
from models.event import *
from models.team import TeamName, Team
from models.actor import Actor
from models.participant import Participant
from src.season import Season
import platform
import pyquery
import datetime
from src.utils import get_driver_path, get_current_season


def download_games(season):
    """
    Download locally the games of a certain season
    :param season: Season object.
    """
    Game.save_games(season)
    Game.sanity_check(season)


def download_events(season,driver_path):
    """
    Download locally the games of a certain season
    :param season: Season object.
    """
    Event.save_events(season,driver_path)
    Event.sanity_check_events(driver_path,season)


def insert_teams(season):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    with db.atomic():
        # Create the instances of Team and TeamName.
        logger.info('Retrieving new teams and their historical names.')
        Team.create_instances(season)
        logger.info('All teams for the season are now in the database.\n')


def insert_games(season):
    """
    Extract and insert the information regarding the games of a season.
    :param season: Season object.
    """
    #if season.season == 1994:  # the 1994 season doesn't have standing page.
    #    TeamName.create_harcoded_teams()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    with db.atomic():

        # Games iformation
        logger.info('Retrieving all data from games and store it.\n')

        # Regular season
        competition_phase = 'regular'
        round_phase = None

        list_files=sorted(os.listdir(season.GAMES_PATH))
        for i in range(len(list_files)):
            game_id_file= list_files[i].split("-")[1]
            game_id=game_id_file.split(".")[0]
            try:
                with open(os.path.join(season.GAMES_PATH, str(list_files[i])), 'r', encoding='utf-8') as f:
                    raw_game = f.read()
                    game = Game.create_instance(raw_game=raw_game, id_game_number=game_id,
                                                season=season,
                                                competition_phase=competition_phase,
                                                round_phase=round_phase)
                    Participant.create_instances(raw_game=raw_game, game=game)
            except Exception as e:
                print(e)
                logger.info("Game {} could not be inserted as it didn't exist or had some errors...".format(game_id))

        # Playoff
        competition_phase = 'playoff'
        round_phase = None
        playoff_format = season.get_playoff_format()
        try:
            quarter_finals_limit = 4 * playoff_format[0]
            try:
                semifinals_limit = quarter_finals_limit + 2 * playoff_format[1]
            except Exception as e:
                #print(e)
                pass
        except Exception as e:
            #print(e)
            pass

        relegation_teams = season.get_relegation_teams()  # in some seasons there was a relegation playoff.
        cont = 0
        id_game_number = season.get_number_games_regular_season()
        playoff_end = season.get_number_games()
        while id_game_number < playoff_end:
            id_game_number += 1
            for file in glob.glob(season.GAMES_PATH+str(id_game_number)+"-*"):
                    try:
                        game_id_file = file.split("-")[1]
                        game_id = game_id_file.split(".")[0]
                        with open(os.path.join(str(file)), 'r', encoding='utf-8') as f:
                            raw_game = f.read()

                            # A playoff game might be blank if the series ends before the last game.
                            if re.search(r'<title>ACB.COM</title>', raw_game) \
                                    and (re.search(r'"estverdel"> <', raw_game)
                                         or re.search(r'<font style="font-size : 12pt;">0 |', raw_game)):
                                cont += 1
                                continue

                            game = Game.create_instance(raw_game=raw_game, id_game_number=game_id,
                                                        season=season,
                                                        competition_phase=competition_phase,
                                                        round_phase=round_phase)

                            home_team_name = TeamName.get(
                                (TeamName.team_id == game.team_home_id) & (TeamName.season == season.season)).name
                            away_team_name = TeamName.get(
                                (TeamName.team_id == game.team_away_id) & (TeamName.season == season.season)).name

                            if (home_team_name or away_team_name) in relegation_teams:
                                game.competition_phase = 'relegation_playoff'
                            else:
                                if cont < quarter_finals_limit:
                                    game.round_phase = 'quarter_final'
                                elif cont < semifinals_limit:
                                    game.round_phase = 'semifinal'
                                else:
                                    game.round_phase = 'final'
                                cont += 1

                            game.save()

                            # Create the instances of Participant
                            Participant.create_instances(raw_game=raw_game, game=game)
                    except Exception as e:
                        print(e)
                        logger.info("Game {} could not be inserted as it didn't exist or had some errors...".format(game_id))
        """
        else:
                # Games iformation
                logger.info('Retrieving all data from games and store it.\n')

                # Regular season
                competition_phase = 'regular'
                round_phase = None

                game_events_ids = season.get_game_events_ids()

                game_ids_list = list(game_events_ids.values())

                for i in range(len(game_ids_list)):
                    try:
                        with open(
                                os.path.join('.', 'data', str(season.season), 'games', str(game_ids_list[i]) + '.html'),
                                'r', encoding='utf-8') as f:
                            raw_game = f.read()
                            game = Game.create_instance(raw_game=raw_game, id_game_number=game_ids_list[i],
                                                        season=season,
                                                        competition_phase=competition_phase,
                                                        round_phase=round_phase)
                            Participant.create_instances(raw_game=raw_game, game=game)
                    except Exception as e:
                        print(e)
                        logger.info("Game {} could not be inserted as it didn't exist or had some errors...".format(
                            game_ids_list[i]))

                # Playoff
                competition_phase = 'playoff'
                round_phase = None
                playoff_format = season.get_playoff_format()
                try:
                    quarter_finals_limit = 4 * playoff_format[0]
                    try:
                        semifinals_limit = quarter_finals_limit + 2 * playoff_format[1]
                    except Exception as e:
                        # print(e)
                        pass
                except Exception as e:
                    # print(e)
                    pass

                relegation_teams = season.get_relegation_teams()  # in some seasons there was a relegation playoff.
                cont = 0
                id_game_number = season.get_number_games_regular_season()
                playoff_end = season.get_number_games()

                while id_game_number < playoff_end:
                    id_game_number += 1
                    try:
                        with open(os.path.join('.', 'data', str(season.season), 'games', str(id_game_number) + '.html'),
                                  'r', encoding='utf-8') as f:
                            raw_game = f.read()

                            # A playoff game might be blank if the series ends before the last game.
                            if re.search(r'<title>ACB.COM</title>', raw_game) \
                                    and (re.search(r'"estverdel"> <', raw_game)
                                         or re.search(r'<font style="font-size : 12pt;">0 |', raw_game)):
                                cont += 1
                                continue

                            game = Game.create_instance(raw_game=raw_game, id_game_number=id_game_number,
                                                        season=season,
                                                        competition_phase=competition_phase,
                                                        round_phase=round_phase)

                            home_team_name = TeamName.get(
                                (TeamName.team_id == game.team_home_id) & (TeamName.season == season.season)).name
                            away_team_name = TeamName.get(
                                (TeamName.team_id == game.team_away_id) & (TeamName.season == season.season)).name

                            if (home_team_name or away_team_name) in relegation_teams:
                                game.competition_phase = 'relegation_playoff'
                            else:
                                if cont < quarter_finals_limit:
                                    game.round_phase = 'quarter_final'
                                elif cont < semifinals_limit:
                                    game.round_phase = 'semifinal'
                                else:
                                    game.round_phase = 'final'
                                cont += 1

                            game.save()

                            # Create the instances of Participant
                            Participant.create_instances(raw_game=raw_game, game=game)
                    except Exception as e:
                        print(e)
                        logger.info("Game {} could not be inserted as it didn't exist or had some errors...".format(
                            game_ids_list[i]))

            """
def update_games():
    """
    Update the information about teams and actors and correct errors.
    """
    # Download actor's page.
    Actor.save_actors()
    Actor.sanity_check()

    with db.atomic():
        try:
            Participant.fix_participants()  # there were a few errors in acb. Manually fix them.
        except Exception as e:
            print(e)
            pass
        Actor.update_content()


def insert_events(season):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    year=season.season

    logger.info('Retrieving all data from events and store it.\n')

    if year >= 2016:
        for game_id_file in os.listdir(season.EVENTS_PATH):
            with open('./data/{}/events/{}'.format(season.season,game_id_file), 'r', encoding='utf-8') as f:
                game_event_acbid = os.path.splitext(game_id_file)[0]
                game_acbid=game_event_acbid.split("-")[0]
                event_acbid = game_event_acbid.split("-")[1]
                content = f.read()
                doc = pyquery.PyQuery(content)
                playbyplay = doc('#playbyplay')
                team_code_1 = doc('.id_aj_1_code').text()
                team_code_2 = doc('.id_aj_2_code').text()
                try:
                    query = Event.select().where(Event.event_acbid == event_acbid)
                    if not query:
                        Event.scrap_and_insert(event_acbid,game_acbid, playbyplay, team_code_1, team_code_2)
                    else:
                        continue
                except Exception as e:
                    print(e,game_id_file)
    else:
        pass


def main(args):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info('STARTING...')

    current_season=get_current_season()

    first_season = args.first_season
    last_season = args.last_season+1

    if args.u:
        if args.first_season == current_season or args.last_season == current_season:
            print("ERROR: first season or last season can't be equal to the current season {} if using argument -u".format(current_season))
            print("USAGE: use -u option to download and insert data for the current season")
            exit(-1)

    if args.r: #reset the database and create the schema.
        reset_database()
        create_schema()

    if args.c: #clean previous records from DB and set auto_increment=1
        delete_records()

    if args.d:  # download the games and events.

        driver_path = args.driver_path

        if not driver_path:
            driver_path = get_driver_path(driver_path)

        for year in reversed(range(first_season, last_season)):
            logger.info('Retrieving data for season '+str(year)+'...\n')
            if year < 2016:
                logger.info('Creating and downloading the season: {}.\n'.format(year))
                season = Season(year)
                download_games(season)
            else:
                season = Season(year)
                download_games(season)
                download_events(season,driver_path)

    if args.i:

        # Extract and insert the information in the database.
        for year in reversed(range(first_season, last_season)):
            logger.info('Inserting data into database for season '+str(year)+'...\n')
            if year < 2016:
                season = Season(year)
                insert_teams(season)
                insert_games(season)
            else:
                season = Season(year)
                insert_teams(season)
                insert_games(season)
                insert_events(season)

        # Update missing info about actors, teams and participants.
        update_games()

    if args.u:

        current_season=get_current_season()

        driver_path = args.driver_path

        if not driver_path:
            driver_path = get_driver_path(driver_path)

        season = Season(current_season)

        Game.save_current_games(season)
        Game.sanity_check(season)

        Event.save_current_events(season, driver_path)
        Event.sanity_check_events(driver_path,season)

        insert_teams(season)
        insert_games(season)
        update_games()
        insert_events(season)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", action='store_true', default=False)
    parser.add_argument("-d", action='store_true', default=False)
    parser.add_argument("-i", action='store_true', default=False)
    parser.add_argument("-c", action='store_true', default=False)
    parser.add_argument("-u", action='store_true', default=False)
    parser.add_argument("--start", action='store', dest="first_season", default=1995, type=int)
    parser.add_argument("--end", action='store', dest="last_season", default=2017, type=int)
    parser.add_argument("--driverpath", action='store', dest="driver_path", default=False)

    main(parser.parse_args())