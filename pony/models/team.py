from pony.models import base
from pony.models.user import User


class Team(base.BaseModel):
    """Team standup."""
    title = base.CharField(index=True, unique=True, max_length=64)
    channel = base.CharField(max_length=64)
    ask_earliest = base.TimeField()
    report_by = base.TimeField()
    is_active = base.BooleanField(default=True)

    class Meta:
        db_table = 'teams'


class UserTeam(base.BaseModel):
    """User to team many-to-many relation."""
    user = base.ForeignKeyField(User, backref='users')
    team = base.ForeignKeyField(Team, backref='teams')

    class Meta:
        db_table = 'user_teams'
