from pony.models import base
from pony.models.user import User
from pony.models.team import Team


class Report(base.BaseModel):
    """Report."""
    user = base.ForeignKeyField(User)
    team = base.ForeignKeyField(Team)
    contents = base.TextField(default='')

    class Meta:
        db_table = 'reports'
