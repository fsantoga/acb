import os.path
from pyquery import PyQuery as pq
from peewee import ForeignKeyField
from src.download import File, DownloadManager
from models.basemodel import BaseModel
from peewee import (PrimaryKeyField, CharField, IntegerField)
from tools.log import logger
from variables import TEAMS_PATH, validate_dir
import re


class Team(BaseModel):
    """
    Class representing a Team.

    A team is basically defined by an acb id, and not a name.
    Because the name of a team can change between seasons (and even in a same season).
    """
    id = IntegerField(primary_key=True)
    founded_year = IntegerField(null=True)

    @staticmethod
    def download_teams(season):
        """
        Downloads the data related to teams of a season.
        :param season:
        :return:
        """
        # Download manager object
        dm = DownloadManager()

        # Get the teams of the season
        teams = Team.get_teams(season, download_manager=dm)
        for team_id in teams.keys():
            Team._download_team_information_webpage(team_id, dm)
            Team._download_roster(team_id, season, dm)
        logger.info(f"Download finished! (new {len(teams)} teams in {season.TEAMS_PATH})\n")

    @staticmethod
    def create_instances(season):
        """
        Inserts the teams and teamnames of a season in the database.

        :param season: int
        :return:
        """
        teams_ids = Team.get_teams(season)
        for team_id, team_name in teams_ids.items():
            team, created = Team.get_or_create(**{'id': team_id})
            if created:
                logger.info(f"New team created in the database: {team.id}")
            if not team.founded_year:
                team.update_founded_year()
            # Insert the team name for that season.
            TeamName.create_instance(team_id, team_name, season)

    @staticmethod
    def get_teams(season, download_manager=None):
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
            file = File(teams_filename)
            season_page = file.open_or_download(url=teams_url, download_manager=download_manager)
            return season_page

        # First call to http://www.acb.com/club
        if download_manager:
            download_manager.send_request('http://www.acb.com/club')

        content = _get_season_page(season)
        parser_string = f"<div class=\"foto\"><a href=\"/club/plantilla/id/([0-9]+)/temporada_id/{season.season}\" title=\"(.*?)\">"
        teams = re.findall(r''+parser_string, content, re.DOTALL)
        teams = [(int(team_id), team_name) for team_id, team_name in teams]  # convert ids to int
        teams = dict(teams)
        logger.info(f"There are {len(teams)} teams: {teams}")

        return teams

    def update_founded_year(self):
        """
        Updates the founded year of the team in the database.
        :return:
        """
        content = Team._download_team_information_webpage(self.id)

        # Extract founded_year from webpage
        doc = pq(content)
        club_data = doc("section[class='datos_club f-l-a-100']")
        club_data = club_data("div[class='fila f-l-a-100 border_bottom']").eq(1)
        title = club_data("div[class='titulo roboto_bold']").text()
        founded_year = club_data("div[class='datos']").text()

        assert title == 'AÑO FUNDACIÓN:', title
        assert founded_year and founded_year != '', self.id
        self.founded_year = int(founded_year)
        self.save()

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
    def _download_team_information_webpage(team_id, download_manager=None):
        """
        Downloads the team information webpage.

        :param season:
        :param team_id:
        :return:
        """
        filename = os.path.join(TEAMS_PATH, str(team_id) + '-information.html')
        file = File(filename)
        url = os.path.join(f"http://www.acb.com/club/informacion/id/{str(team_id)}")
        logger.info(f"Retrieving information page from: {url}")
        return file.open_or_download(url=url, download_manager=download_manager)

    @staticmethod
    def _download_roster(team_id, season, download_manager):
        """
        Downloads the roster of a team of a given season.
        :param team_id:
        :param season:
        :return:
        """
        # First call to main team webpage
        download_manager.send_request(f"http://www.acb.com/club/plantilla/id/{team_id}/")

        filename = os.path.join(season.TEAMS_PATH, str(team_id) + '-roster.html')
        file = File(filename)
        url = os.path.join(f"http://www.acb.com/club/plantilla/id/{str(team_id)}/temporada_id/{season.season}")
        logger.info(f"Retrieving roster page from: {url}")
        return file.open_or_download(url=url, download_manager=download_manager)


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
    def create_instance(team_id, team_name, season):
        """
        Creates a TeamName instance for a team and season.
        :param team:
        :param season:
        :return:
        """
        team_name_dict = {'team_id': team_id, 'name': team_name, 'season': season.season}
        TeamName.get_or_create(**team_name_dict)