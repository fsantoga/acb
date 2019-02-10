from models.basemodel import BaseModel
from models.team import Team
from peewee import (PrimaryKeyField, ForeignKeyField)


class Roster(BaseModel):
    id = PrimaryKeyField()
    event_id = ForeignKeyField(Team, index=True, null=True)
    actor_id = ForeignKeyField(Team, index=True, null=True)

