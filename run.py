import argparse, os, re,glob
from models.basemodel import db, reset_database, delete_records, create_schema
from models.event import *
from models.team import TeamName, Team
from models.actor import Actor
from models.participant import Participant
from ml.utils_ml import *
from src.season import Season
import pyquery
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
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    with db.atomic():

        # Games iformation
        logger.info('Retrieving all data from games and storing it.')

        n_regular = season.get_number_games_regular_season()

        # Specific info for the playoffs
        relegation_teams = season.get_relegation_teams()  # in some seasons there was a relegation playoff.
        cont = 0
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

        # For all games available
        list_files=sorted(os.listdir(season.GAMES_PATH))
        for file_name in list_files:
            game_number = int(file_name.split("-")[0])
            game_acbid = int(file_name.split("-")[1].split(".")[0])

            if game_number <= n_regular:  # Regular season
                competition_phase = 'regular'
                round_phase = None
                try:
                    with open(os.path.join(season.GAMES_PATH, file_name), 'r', encoding='utf-8') as f:
                        raw_game = f.read()
                        game = Game.create_instance(raw_game=raw_game, game_acbid=game_acbid,
                                                    season=season,
                                                    competition_phase=competition_phase,
                                                    round_phase=round_phase)
                        Participant.create_instances(raw_game=raw_game, game=game)
                except Exception as e:
                    print(e)
                    logger.info(
                        "Game {} could not be inserted as it didn't exist or had some errors...".format(game_acbid))

            else:  # Playoff
                competition_phase = 'playoff'
                round_phase = None
                try:
                    with open(os.path.join(season.GAMES_PATH, file_name), 'r', encoding='utf-8') as f:
                        raw_game = f.read()

                        # A playoff game might be blank if the series ends before the last game.
                        if re.search(r'<title>ACB.COM</title>', raw_game) \
                                and (re.search(r'"estverdel"> <', raw_game)
                                     or re.search(r'<font style="font-size : 12pt;">0 |', raw_game)):
                            cont += 1
                            continue

                        game = Game.create_instance(raw_game=raw_game, game_acbid=game_acbid,
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
                    logger.info("Game {} could not be inserted as it didn't exist or had some errors...".format(game_acbid))


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

    logger.info('Retrieving all data from events and storing it.')

    if year >= 2016:
        for game_id_file in os.listdir(season.EVENTS_PATH):
            with open('./data/{}/events/{}'.format(season.season,game_id_file), 'r', encoding='utf-8') as f:
                game_event_acbid = os.path.splitext(game_id_file)[0]
                game_acbid=game_event_acbid.split("-")[0]
                events_game_acbid = game_event_acbid.split("-")[1]
                content = f.read()
                doc = pyquery.PyQuery(content)
                playbyplay = doc('#playbyplay')
                query_teams = Game.get(Game.game_acbid == game_acbid)
                team_home_id = query_teams.team_home_id
                team_away_id = query_teams.team_away_id

                try:
                    query = Event.select().where(Event.events_game_acbid == events_game_acbid)
                    if not query:
                        Event.scrap_and_insert(events_game_acbid, game_acbid, playbyplay, team_home_id, team_away_id)
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
    last_season = args.last_season

    season=Season(current_season)

    if first_season > last_season:  # dates checking
        logger.error("ERROR: First season must be lower or equal than the last season to download.")
        logger.error("USAGE: use --start YEAR and --end YEAR options to specify the seasons properly.")
        exit(-1)

    if first_season > current_season or last_season > current_season:
        logger.error("ERROR: First season and last season must be lower or equal than the current season {}".format(current_season))
        logger.error("USAGE: use --start YEAR and --end YEAR options to specify the seasons properly or -u for the current season only.")
        exit(-1)

    if args.r:  # Reset the database and create the schema
        reset_database()
        create_schema()

    if args.c:  # Clean previous records from DB and set auto_increment=1
        delete_records()

    if args.d:  # Download the games and events
        driver_path = args.driver_path
        if not driver_path:
            driver_path = get_driver_path(driver_path)

        for year in reversed(range(first_season, last_season + 1)):
            logger.info('Retrieving data for season '+str(year)+'...\n')
            season = Season(year)
            download_games(season)
            if year >= 2016:
                download_events(season,driver_path)

    if args.i:  # Extract and insert the information in the database.
        for year in reversed(range(first_season, last_season + 1)):
            logger.info('Inserting data into database for season '+str(year)+'...\n')
            season = Season(year)
            insert_teams(season)
            insert_games(season)
            if year >= 2016:
                insert_events(season)

        # Update missing info about actors and participants.
        update_games()

    if args.u:  # Download and insert the information for the current season
        driver_path = args.driver_path
        if not driver_path:
            driver_path = get_driver_path(driver_path)
        season = Season(current_season)
        download_games(season)
        download_events(season, driver_path)
        insert_teams(season)
        insert_games(season)
        insert_events(season)
        update_games()

    if args.t:
        print("TRAIN")
    if args.p:
        print("PREDICT")

        if args.journey:
            journey=args.journey
            journey_matches_ml = get_journey_matches(season, journey)
            print(journey_matches_ml)
        else:
            #current_journey_matches_ml = get_current_journey_matches(season)
            #print(current_journey_matches_ml)

            next_journey_matches_ml = get_next_journey_matches(season)
            print(next_journey_matches_ml)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-r", action='store_true', default=False) #Reset database
    parser.add_argument("-d", action='store_true', default=False) #Download
    parser.add_argument("-i", action='store_true', default=False) #Insert
    parser.add_argument("-c", action='store_true', default=False) #clean previous records DB
    parser.add_argument("-u", action='store_true', default=False) #Update DB with new games
    parser.add_argument("-p", action='store_true', default=False) #Predict next results
    parser.add_argument("-t", action='store_true', default=False) #Train ML model

    parser.add_argument("--journey", action='store', dest="journey", type=int)
    parser.add_argument("--start", action='store', dest="first_season", default=2018, type=int)
    parser.add_argument("--end", action='store', dest="last_season", default=2018, type=int)
    parser.add_argument("--driverpath", action='store', dest="driver_path", default=False)

    main(parser.parse_args())