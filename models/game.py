import os.path, re, datetime, difflib, logging
from pyquery import PyQuery as pq
from src.download import open_or_download, get_page, sanity_check_game,sanity_check_game_copa
from src.season import BASE_URL
from models.basemodel import BaseModel
from models.team import Team, TeamName
from peewee import (PrimaryKeyField, IntegerField, DateTimeField, ForeignKeyField, BooleanField, CharField)
from src.utils import get_current_season
from utils.log import logger, init_logging

init_logging('game.log')


class Game(BaseModel):
    """
    Class representing a Game.

    A game only contains basic information about the game and the scores.
    """
    id = PrimaryKeyField()
    game_acbid = IntegerField(unique=True, index=True)
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
    def save_games(season, logging_level=logging.INFO):
        """
        Method for saving locally the games of a season.

        :param season: int
        :param logging_level: logging object
        :return:
        """
        logger.info('Starting the download of games...')

        if season.season == get_current_season():
            current_game_events_ids = season.get_current_game_events_ids()
            game_ids_list = list(current_game_events_ids.values())
        else:
            game_ids_list = season.get_game_ids()


        n_checkpoints = 4
        checkpoints = [round(i * float(len(game_ids_list)) / n_checkpoints) for i in range(n_checkpoints + 1)]
        for i in range(len(game_ids_list)):
            game_id = int(game_ids_list[i]) % 1000
            url2 = BASE_URL + "/fichas/LACB{}.php".format(game_ids_list[i])
            filename = os.path.join(season.GAMES_PATH, str(game_id)+"-" +str(game_ids_list[i]) + '.html')

            open_or_download(file_path=filename, url=url2)
            if i in checkpoints:
                logger.info('{}% already downloaded'.format(round(float(i * 100) / len(game_ids_list))))

        logger.info('Download finished! (new {} games in {})\n'.format(len(game_ids_list), season.GAMES_PATH))


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


    @staticmethod
    def create_instance(raw_game, game_acbid, season, competition_phase,round_phase=None):
        """
        Extract all the information regarding the game such as the date, attendance, venue, score per quarter or teams.
        Therefore, we need first to extract and insert the teams in the database in order to get the references to the db.

        :param raw_game: String
        :param game_acbid: int
        :param season: Season
        :param competition_phase: String
        :param round_phase: String
        :return: Game object
        """
        # There are two different statistics table in acb.com. I assume they created the new one to introduce the +/- stat.
        estadisticas_tag = '.estadisticasnew' if re.search(r'<table class="estadisticasnew"', raw_game) else '.estadisticas'

        doc = pq(raw_game)
        game_dict = dict()

        """
        Each game has an unique id in acb.com. The id has 5 digits, where the first two digits are the season code (the
        oldest season in 1956 has code 1) and the three last are the number of the game (a simple counter since the beginning
        of the season).

        This id can be used to access the concrete game within the link 'http://www.acb.com/fichas/LACBXXYYY.php'
        """
        game_dict['game_acbid'] = game_acbid
        game_dict['season'] = season.season
        game_dict['competition_phase'] = competition_phase
        game_dict['round_phase'] = round_phase


        # Information about the teams.
        info_teams_data = doc(estadisticas_tag).eq(1)
        home_team_name = None
        away_team_name = None

        """
        We only have the names of the teams (text) within the doc. We will look for its associated id by looking in our teamname table, where
        we have all the historical official names for each team and season. However the ACB sometimes doesn't agree in the names
        and writes them in different ways depending on the game (sometimes taking older names or making small changes).
        For instance VALENCIA BASKET CLUB instead of VALENCIA BASKET.
        So if there is not such a direct correspondance we will take the closest match.
        """
        for i in [0, 2]:
            team_data = info_teams_data('.estverde').eq(i)('td').eq(0).text()
            team_name = re.search("(.*) [0-9]", team_data).groups()[0]

            try:  ## In case the name of the team is exactly the same as one stated in our database for a season
                team_acbid = TeamName.get(TeamName.name == team_name).team_id.team_acbid
                team = Team.get(Team.team_acbid == team_acbid)

            except TeamName.DoesNotExist:  ## In case there is not an exact correspondance within our database, let's find the closest match.
                query = TeamName.select(TeamName.team_id, TeamName.name)
                teams_names_ids = dict()
                for q in query:
                    teams_names_ids[q.name] = q.team_id.id

                most_likely_team = difflib.get_close_matches(team_name, teams_names_ids.keys(), 1, 0.4)[0]
                team = Team.get(Team.id == teams_names_ids[most_likely_team])

                if most_likely_team not in season.mismatched_teams:  # debug info to check the correctness.
                    season.mismatched_teams.append(most_likely_team)
                    logger.info('Season {} -> {} has been matched to: {}'.format(season.season, team_name, most_likely_team))

            # TeamName.get_or_create(**{'team': team, 'name': team_name, 'season': season.season})
            game_dict['team_home_id' if i == 0 else 'team_away_id'] = team
            home_team_name = team_name if i == 0 else home_team_name
            away_team_name = team_name if i != 0 else away_team_name

        # Information about the game.
        info_game_data = doc(estadisticas_tag).eq(0)

        scheduling_data = info_game_data('.estnegro')('td').eq(0).text()
        scheduling_data = scheduling_data.split("|")
        journey, date, time, venue, attendance = list(map(lambda x: x.strip(), scheduling_data))  # Remove extra spaces.

        if date and time:
            day, month, year = list(map(int, date.split("/")))
            hour, minute = list(map(int, time.split(":")))
            game_dict['kickoff_time'] = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute)

        if attendance:
            try:
                game_dict['attendance'] = int(attendance.split(":")[1])
            except ValueError:
                pass

        if venue:
            game_dict['venue'] = venue

        if journey:
            game_dict['journey'] = journey.split(" ")[1]

        if competition_phase=='cup':
            if int(journey.split(" ")[1])==1:
                game_dict['round_phase'] ="quarter_final"
            elif int(journey.split(" ")[1])==2:
                game_dict['round_phase'] ="semi_final"
            elif int(journey.split(" ")[1])==3:
                game_dict['round_phase'] ="final"

        for i in range(2, 7):
            score_home_attribute = ''
            score_away_attribute = ''
            if i == 2:
                score_home_attribute = 'score_home_first'
                score_away_attribute = 'score_away_first'
            elif i == 3:
                score_home_attribute = 'score_home_second'
                score_away_attribute = 'score_away_second'
            elif i == 4:
                score_home_attribute = 'score_home_third'
                score_away_attribute = 'score_away_third'
            elif i == 5:
                score_home_attribute = 'score_home_fourth'
                score_away_attribute = 'score_away_fourth'
            elif i == 6:
                score_home_attribute = 'score_home_extra'
                score_away_attribute = 'score_away_extra'

            quarter_data = info_game_data('.estnaranja')('td').eq(i).text()
            if quarter_data:
                try:
                    game_dict[score_home_attribute], game_dict[score_away_attribute] = list(
                        map(int, quarter_data.split("|")))
                except ValueError:
                    pass

        referees_data = info_game_data('.estnaranja')('td').eq(0).text()
        if referees_data:
            referees = referees_data.split(":")[1].strip().split(",")
            referees = list(filter(None, referees))
            referees = list(map(lambda x: x.strip(), referees))
            n_ref = 1
            for referee in referees:
                game_dict['referee_'+str(n_ref)] = referee
                n_ref+=1

        try:
            game = Game.get(Game.game_acbid == game_dict['game_acbid'])
        except:
            game = Game.create(**game_dict)
        return game


from src.season import Season
s = Season(2017)
Game.save_games(s)