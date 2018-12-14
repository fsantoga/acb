import os.path, logging
from pyquery import PyQuery as pq
from peewee import ForeignKeyField
from src.download import open_or_download
from models.basemodel import BaseModel
from peewee import (PrimaryKeyField, CharField, IntegerField)
from src.season import BASE_URL, TEAMS_PATH, FIRST_SEASON, LAST_SEASON


class Team(BaseModel):
    """
    Class representing a Team.

    A team is basically defined by an acb id, and not a name.
    Because the name of a team can change between seasons (and even in a same season).
    """
    id = PrimaryKeyField()
    team_acbid = CharField(max_length=3, unique=True, index=True)
    founded_year = IntegerField(null=True)

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
                teams_names = []  # Look for all historical team names and save them
                for s in range(1, LAST_SEASON - FIRST_SEASON + 2):
                    filename = os.path.join(TEAMS_PATH, team_acbid + str(s) + '.html')
                    url = os.path.join(BASE_URL, 'club.php?cod_competicion=LACB&cod_edicion={}&id={}'.format(s, team_acbid))
                    content = open_or_download(file_path=filename, url=url)
                    doc = pq(content)
                    team_name_season = doc('#portadadertop').eq(0).text().upper()
                    if team_name_season != '':
                        teams_names.append({'team_id': team.id, 'name': str(team_name_season), 'season': FIRST_SEASON + s - 1})
                TeamName.insert_many(teams_names).on_conflict('IGNORE').execute()
                try:
                    # Add the year of foundation (from last url content)
                    if doc('.titulojug').eq(0).text().startswith('Año de fundac'):
                        team.founded_year = int(doc('.datojug').eq(0).text())
                        team.save()
                except:
                    founded_year=team.get_hardcoded_foundation_years(team_acbid)
                    if founded_year!=None:
                        team.founded_year=founded_year
                        team.save()
                        logging.info("Team {} doesn't have foundation year. Hardcoded with year: {}".format(team_acbid,founded_year))
                    else:
                        logging.info("Team {} doesn't have foundation year. No matches found.".format(team_acbid))
                        pass

    @staticmethod
    def get_hardcoded_foundation_years(team_acbid):

        hardcoded_teams = {
            'LEO': '1981',
            'SAL': '1993',
            'ZAR': '1981',
            'HUE': '1977',
            'HLV': '1996'
        }
        year=hardcoded_teams.get(team_acbid)
        return year


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

