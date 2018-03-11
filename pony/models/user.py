from pony.models import base


class User(base.BaseModel):
    """User."""
    user_id = base.CharField(max_length=16)
    full_name = base.CharField(max_length=128)
    email = base.CharField(max_length=128)
    color = base.CharField(max_length=8)
    timezone = base.CharField(max_length=128)
    image_url = base.CharField(max_length=512)
    is_deleted = base.BooleanField(default=False)
    is_admin = base.BooleanField(default=False)
    is_owner = base.BooleanField(default=False)

    class Meta:
        db_table = 'users'
