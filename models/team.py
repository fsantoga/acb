import os.path, logging
from pyquery import PyQuery as pq
from peewee import ForeignKeyField
from src.download import open_or_download
from models.basemodel import BaseModel
from peewee import (PrimaryKeyField, TextField, CharField, IntegerField)
from src.season import BASE_URL, TEAMS_PATH, FIRST_SEASON, LAST_SEASON


class Team(BaseModel):
    """
    Class representing a Team.

    A team is basically defined by an acb id, and not a name.
    Because the name of a team can change between seasons (and even in a same season).
    """
    id = PrimaryKeyField()
    acbid = CharField(max_length=3, unique=True, index=True)
    founded_year = IntegerField(null=True)

    @staticmethod
    def create_instances(season):
        """
        Create the database instances of the teams.
        :param season: int
        :return:
        """
        teams_ids = season.get_teams_ids()
        for acbid in teams_ids:
            team, created = Team.get_or_create(**{'acbid': acbid})
            """
            Whenever we introduce a new Team in our database we will also store all its historical names in team names.
            Note that we have a TeamName for a single team and season, as those may change due to the sponsors.  
            However, the same teams always have the same acbid and we can link them.
            """
            if created:
                teams_names = []
                for s in range(1, LAST_SEASON - FIRST_SEASON + 2):
                    filename = os.path.join(TEAMS_PATH, acbid + str(s) + '.html')
                    url = os.path.join(BASE_URL, 'club.php?cod_competicion=LACB&cod_edicion={}&id={}'.format(s, acbid))
                    content = open_or_download(file_path=filename, url=url)
                    doc = pq(content)
                    team_name_season = doc('#portadadertop').eq(0).text().upper()
                    if team_name_season != '':
                        teams_names.append({'team_id': team.id, 'name': str(team_name_season), 'season': FIRST_SEASON + s - 1})
                TeamName.insert_many(teams_names).on_conflict('IGNORE').execute()

    @staticmethod
    def update_content(logging_level=logging.INFO):
        """
        First we insert the instances in the database with basic information and later we update the rest of fields.
        We update the information of the teams that have not been filled yet in the database.
        """
        logging.basicConfig(level=logging_level)
        logger = logging.getLogger(__name__)

        logger.info('Starting to update the teams that have not been filled yet...')
        teams = Team.select().where(Team.founded_year >> None)
        for cont, team in enumerate(teams):
            team._update_content()
            try:
                if len(teams) and cont % (round(len(teams) / 3)) == 0:
                    logger.info('{}% already updated'.format(round(float(cont) / len(teams) * 100)))
            except ZeroDivisionError:
                pass

        logger.info('Update finished! ({} teams)\n'.format(len(teams)))

    def _update_content(self):
        """
        First we insert the instances in the database with basic information and later we update the rest of fields.
        :return:
        """
        from src.season import BASE_URL, TEAMS_PATH
        filename = os.path.join(TEAMS_PATH, self.acbid + '.html')
        url = os.path.join(BASE_URL, 'club.php?cod_competicion=LACB&id={}'.format(self.acbid))
        content = open_or_download(file_path=filename, url=url)
        try:
            self.founded_year = self._get_founded_year(content)
            self.save()
        except ValueError:
            pass

    def _get_founded_year(self, raw_team):
        """
        Extract the founded year of a team.
        :param raw_team: String
        :return: founded year
        """
        doc = pq(raw_team)

        if doc('.titulojug').eq(0).text().startswith('Año de fundac'):
            return int(doc('.datojug').eq(0).text())
        else:
            raise Exception('The first field is not the founded year.')


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
    def create_instance(team_name, acbid, season):
        """
        Create an instance of a TeamName

        :param team_name: String
        :param acbid: String
        :param season: int
        """
        team = Team.get(Team.acbid == acbid)
        TeamName.get_or_create(**{'name': team_name, 'team': team, 'season': season})

