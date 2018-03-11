from datetime import datetime

from peewee import *


class DatabaseConnectionManager(object):
    database = SqliteDatabase(None)

    @classmethod
    def initialize(cls, config):
        cls.database.init('x' + config['db_file'])
        cls.database.connect()

    @classmethod
    def close(cls):
        cls.database.close()


class BaseModel(Model):
    """Base model for all the models."""
    id = AutoField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        super(BaseModel, self).save(*args, **kwargs)

    class Meta:
        database = DatabaseConnectionManager.database
        only_save_dirty = True
