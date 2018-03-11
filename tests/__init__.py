import os
import sys
sys.path.insert(0, os.path.abspath('..'))

from pony.models import models, DatabaseConnectionManager


DatabaseConnectionManager.initialize({'db_file': 'test.db'})
with DatabaseConnectionManager.database:
    DatabaseConnectionManager.database.drop_tables(models, fail_silently=True)
    DatabaseConnectionManager.database.create_tables(models)
