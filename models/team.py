import os.path
from pyquery import PyQuery as pq
from peewee import ForeignKeyField
from src.download import open_or_download
from models.basemodel import BaseModel
from peewee import (PrimaryKeyField, CharField, IntegerField)
from src.season import BASE_URL, TEAMS_PATH, FIRST_SEASON, LAST_SEASON
from tools.log import logger


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

    def update_founded_year(self):
        content = self._download_team_information_page()

        # Extract founded_year from webpage
        doc = pq(content)
        club_data = doc("section[class='datos_club f-l-a-100']")
        club_data = club_data("div[class='fila f-l-a-100 border_bottom']").eq(1)
        title = club_data("div[class='titulo roboto_bold']").text()
        founded_year = club_data("div[class='datos']").text()

        assert title == 'AÑO FUNDACIÓN:', title
        assert founded_year != ''
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

    def _download_team_information_page(self):
        filename = os.path.join(TEAMS_PATH, self.team_acbid + '-information.html')
        url = os.path.join(BASE_URL, f"club/informacion/id/{self.team.team_acbid}")
        logger.info(f"Retrieving information page for foundation year from: {url}")
        content = open_or_download(file_path=filename, url=url)
        return content

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

    @staticmethod
    def populate(team):
        def _download_team_webpage(team, season):
            filename = os.path.join(TEAMS_PATH, team.team_acbid + '-' + season + '.html')
            url = os.path.join(BASE_URL, f"club/plantilla/id/{team.team_acbid}/temporada_id/{season}")
            logger.info(f"Retrieving information of the team from: {url}")

            cookies = {
                'acepta_uso_cookies': '1',
                'forosacbcom_u': '1',
                'forosacbcom_k': '',
                'forosacbcom_sid': 'FFD~21d43aee99bee89138ba91bc285687d4',
                'PHPSESSID': 'neq0ak7jfjv1spa5ion3gkm43r',
            }
            content = open_or_download(file_path=filename, url=url, cookies=cookies)
            return content

        def _get_team_name(from_content, team, season):
            doc = pq(from_content)
            team_name_season = doc("div[id='listado_equipo_nacional']")
            team_name_season = team_name_season(f"div[data-t2v-id='{team.team_acbid}']").text().upper()
            if team_name_season != '':
                logger.info(f"Season: {season}; Team name: {team_name_season}")
                return {'team_id': team.id, 'name': str(team_name_season), 'season': int(season)}
            return

        # TODO: why do we need all the names from previous season????
        # TODO: maybe just take the name from this year, and the combine in the database from previous years?
        # TODO: or have another logic...
        teams_names = []  # Look for all historical team names and save them
        for season_id in range(1, LAST_SEASON - FIRST_SEASON + 2):
            season = FIRST_SEASON + season_id - 1
            season = str(season)
            content = _download_team_webpage(team=team, season=season)
            team_name_dict = _get_team_name(from_content=content, team=team, season=season)
            if team_name_dict:
                teams_names.append(team_name_dict)
        TeamName.insert_many(teams_names).on_conflict('IGNORE').execute()
