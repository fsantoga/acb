import argparse, os, re
from models.basemodel import db, reset_database, delete_records, create_schema
from models.game import Game
from models.event import *
from models.team import TeamName, Team
from models.actor import Actor
from models.participant import Participant
from src.season import Season
import platform
import pyquery


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
        # Create the instances of Team.
        Team.create_instances(season)

        # Regular season
        competition_phase = 'regular'
        round_phase = None
        for id_game_number in range(1, season.get_number_games_regular_season() + 1):
            try:
                with open(os.path.join('.', 'data', str(season.season), 'games', str(id_game_number) + '.html'), 'r', encoding='utf-8') as f:
                    raw_game = f.read()
                    game = Game.create_instance(raw_game=raw_game, id_game_number=id_game_number,
                                                season=season,
                                                competition_phase=competition_phase,
                                                round_phase=round_phase)
                    Participant.create_instances(raw_game=raw_game, game=game)
            except:
                logger.info("No se ha podido insertar el partido {} porque no existe o contiene errores...".format(id_game_number))

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
            try:
                with open(os.path.join('.', 'data', str(season.season), 'games', str(id_game_number) + '.html'), 'r', encoding='utf-8') as f:
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
            except:
                logger.info("No se ha podido insertar el partido {} porque no existe o contiene errores...".format(id_game_number))


def update_games():
    """
    Update the information about teams and actors and correct errors.
    """
    # Download actor's page.
    Actor.save_actors()
    Actor.sanity_check()

    with db.atomic():
        Team.update_content()
        try:
            Participant.fix_participants()  # there were a few errors in acb. Manually fix them.
        except Exception as e:
            print(e)
            pass
        Actor.update_content()


def insert_events(season):
    year=season.season
    if year >= 2016:
        for game_id_file in os.listdir(season.EVENTS_PATH):
            with open('./data/{}/events/{}'.format(season.season,game_id_file), 'r', encoding='utf-8') as f:
                game_event_id = os.path.splitext(game_id_file)[0]
                game_id=game_event_id.split("-")[0]
                content = f.read()
                doc = pyquery.PyQuery(content)
                playbyplay = doc('#playbyplay')
                team_code_1 = doc('.id_aj_1_code').text()
                team_code_2 = doc('.id_aj_2_code').text()
                try:
                    Event.scrap_and_insert(game_id, playbyplay, team_code_1, team_code_2)
                except Exception as e:
                    print(e,game_id_file)
    else:
        pass


def main(args):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


    first_season = args.first_season
    last_season = args.last_season+1

    if args.r: #reset the database and create the schema.
        reset_database()
        create_schema()

    if args.c: #clean previous records from DB and set auto_increment=1
        delete_records()

    if args.d:  # download the games.
        system = platform.system()
        driver_path = args.driver_path
        if not driver_path:
            if system == "Linux":
                driver_path = "./geckodriver_linux"
            elif system == "Windows":
                driver_path = "./geckodriver_windows"
            else:
                print("ERROR: no --driverpath. When using a system different from Linux/Windows a driver path must be set")
                print("USAGE: --driverpath 'path/to/driver'")
                exit(-1)

            logger.info('No driver specified, using the system one by default ({})...'.format(driver_path))

        for year in reversed(range(first_season, last_season)):
            logger.info('Retrieving data for season '+str(year)+'...')
            if year < 2016:
                season = Season(year)
                download_games(season)
            else:
                season = Season(year)
                download_games(season)
                download_events(season,driver_path)

    if args.i:
        # Extract and insert the information in the database.
        for year in reversed(range(first_season, last_season)):
            logger.info('Inserting data into database for season '+str(year)+'...')
            if year < 2016:
                season = Season(year)
                insert_games(season)
            else:
                season = Season(year)
                insert_games(season)
                insert_events(season)

        # Update missing info about actors, teams and participants.
        update_games()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", action='store_true', default=False)
    parser.add_argument("-d", action='store_true', default=False)
    parser.add_argument("-i", action='store_true', default=False)
    parser.add_argument("-c", action='store_true', default=False)
    parser.add_argument("-u", action='store_true', default=False)
    parser.add_argument("--start", action='store', dest="first_season", default=2015, type=int)
    parser.add_argument("--end", action='store', dest="last_season", default=2018, type=int)
    parser.add_argument("--driverpath", action='store', dest="driver_path", default=False)

    main(parser.parse_args())