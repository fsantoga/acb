import os.path
from pyquery import PyQuery as pq
from peewee import ForeignKeyField
from src.download import open_or_download
from models.basemodel import BaseModel
from peewee import (PrimaryKeyField, CharField, IntegerField)
from tools.log import logger
from variables import TEAMS_PATH
from tools.checkpoint import Checkpoint


class Team(BaseModel):
    """
    Class representing a Team.

    A team is basically defined by an acb id, and not a name.
    Because the name of a team can change between seasons (and even in a same season).
    """
    id = PrimaryKeyField()
    # TODO, change this, it has been changed, now they are integers. Check intervals.
    team_acbid = CharField(max_length=3, unique=True, index=True)
    founded_year = IntegerField(null=True)

    @staticmethod
    def download_teams(season):
        """
        Downloads the data related to teams of a season.
        :param season:
        :return:
        """
        def _download_team_information_webpage(team_id):
            """
            Downloads the team information webpage.

            :param season:
            :param team_id:
            :return:
            """
            filename = os.path.join(TEAMS_PATH, team_id + '-information.html')
            url = os.path.join(f"http://www.acb.com/club/informacion/id/{team_id}")
            logger.info(f"Retrieving information page from: {url}")
            open_or_download(file_path=filename, url=url)

        # Get the teams of the season
        teams = Team._get_teams(season)
        for team_id in teams.keys():
            _download_team_information_webpage(season, team_id)
        logger.info(f"Download finished! (new {len(teams)} teams in {season.GAMES_PATH})\n")

    @staticmethod
    def get_teams(season):
        """
        Extracts the teams for the season (id -> team_name)

        Example of team:
        <a href="/club/plantilla/id/2" class="clase_mostrar_block960 equipo_logo primer_logo">
        <img src="http://static.acb.com/img/32/1d/a/1453105588.png" alt="Barça " /></a>
        :return:
        """
        def _get_season_page(season):
            """
            Saves a webpage containing all the teams of the season.

            E.g.: http://www.acb.com/club/index/temporada_id/2019
            :return:
            """
            teams_filename = os.path.join(season.TEAMS_PATH, 'teams.html')
            teams_url = f"http://www.acb.com/club/index/temporada_id/{season.season}"
            logger.info(f"Downloading teams from {teams_url}")
            season_page = open_or_download(file_path=teams_filename, url=teams_url)
            return season_page

        content = _get_season_page(season)
        doc = pq(content)
        teams = doc("div[class='contenedor_logos_equipos']")

        # Get the teams ids
        teams_ids = teams.items('a')
        teams_ids = [t.attr('href') for t in teams_ids]
        teams_ids = [t.split('/')[-1] for t in teams_ids]

        # Get the teams names
        teams_names = teams.items('img')
        teams_names = [t.attr('alt') for t in teams_names]

        teams = dict(zip(teams_ids, teams_names))
        logger.info(f"There are {len(teams)} teams: {teams}")
        return teams


    # def update_founded_year(self):
    #     content = self._download_team_information_page()
    #
    #     # Extract founded_year from webpage
    #     doc = pq(content)
    #     club_data = doc("section[class='datos_club f-l-a-100']")
    #     club_data = club_data("div[class='fila f-l-a-100 border_bottom']").eq(1)
    #     title = club_data("div[class='titulo roboto_bold']").text()
    #     founded_year = club_data("div[class='datos']").text()
    #
    #     assert title == 'AÑO FUNDACIÓN:', title
    #     assert founded_year != ''
    #     self.founded_year = int(founded_year)
    #     self.save()

        # TODO: Let us assume we do not have errors here...
        # except:
        #     founded_year = team.get_hardcoded_foundation_years(team.team_acbid)
        #     if founded_year != None:
        #         team.founded_year = founded_year
        #         team.save()
        #         logger.info(
        #             "Team {} doesn't have foundation year. Hardcoded with year: {}".format(team.team_acbid, founded_year))
        #     else:
        #         logger.info("Team {} doesn't have foundation year. No matches found.".format(team.team_acbid))

        # @staticmethod
        # def get_hardcoded_foundation_years(team_acbid):
        #     hardcoded_teams = {
        #         'LEO': '1981',
        #         'SAL': '1993',
        #         'ZAR': '1981',
        #         'HUE': '1977',
        #         'HLV': '1996'
        #     }
        #     year = hardcoded_teams.get(team_acbid)
        #     return year



    @staticmethod
    def create_instances(season):
        """
        Create the database instances of the teams.
        Whenever we introduce a new Team in our database we will also store all its historical names in teamnames.
        Note that we have a teamname for a single team and season, as those may change due to the sponsors.
        However, the same teams always have the same acbid so we can link them.
        Besides we will add the founded year.
        :param season: int
        :return:
        """
        teams_ids = season.get_teams_ids()
        for team_acbid in teams_ids:
            team, created = Team.get_or_create(**{'team_acbid': team_acbid})
            if created:  # If the team was not in our database before
                logger.info(f"New team created: {team.team_acbid}")
                TeamName.populate(team)
                Team.update_founded_year(team)


class TeamName(BaseModel):
    """
    Class representing a TeamName.

    The name of a team depends on the season. And even within a season can have several names.
    """
    id = PrimaryKeyField()
    team_id = ForeignKeyField(Team, related_name='names', index=True)
    name = CharField(max_length=255)
    season = IntegerField()

    class Meta:
        indexes = (
            (('name', 'season'), True),
        )

    @staticmethod
    def create_instance(team_name, team_acbid, season):
        """
        Create an instance of a TeamName

        :param team_name: String
        :param acbid: String
        :param season: int
        """
        team = Team.get(Team.team_acbid == team_acbid)
        TeamName.get_or_create(**{'name': team_name, 'team': team, 'season': season})

    # @staticmethod
    # def populate(team):
    #     def _download_team_webpage(team, season):
    #         filename = os.path.join(TEAMS_PATH, team.team_acbid + '-' + season + '.html')
    #         url = os.path.join(BASE_URL, f"club/plantilla/id/{team.team_acbid}/temporada_id/{season}")
    #         logger.info(f"Retrieving information of the team from: {url}")
    #
    #         cookies = {
    #             'acepta_uso_cookies': '1',
    #             'forosacbcom_u': '1',
    #             'forosacbcom_k': '',
    #             'forosacbcom_sid': 'FFD~21d43aee99bee89138ba91bc285687d4',
    #             'PHPSESSID': 'neq0ak7jfjv1spa5ion3gkm43r',
    #         }
    #         content = open_or_download(file_path=filename, url=url, cookies=cookies)
    #         return content
    #
    #     def _get_team_name(from_content, team, season):
    #         doc = pq(from_content)
    #         team_name_season = doc("div[id='listado_equipo_nacional']")
    #         team_name_season = team_name_season(f"div[data-t2v-id='{team.team_acbid}']").text().upper()
    #         if team_name_season != '':
    #             logger.info(f"Season: {season}; Team name: {team_name_season}")
    #             return {'team_id': team.id, 'name': str(team_name_season), 'season': int(season)}
    #         return
    #
    #     # TODO: why do we need all the names from previous season????
    #     # TODO: maybe just take the name from this year, and the combine in the database from previous years?
    #     # TODO: or have another logic...
    #     teams_names = []  # Look for all historical team names and save them
    #     for season_id in range(1, LAST_SEASON - FIRST_SEASON + 2):
    #         season = FIRST_SEASON + season_id - 1
    #         season = str(season)
    #         content = _download_team_webpage(team=team, season=season)
    #         team_name_dict = _get_team_name(from_content=content, team=team, season=season)
    #         if team_name_dict:
    #             teams_names.append(team_name_dict)
    #     TeamName.insert_many(teams_names).on_conflict('IGNORE').execute()
