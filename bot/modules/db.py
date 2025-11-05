from global_modules.db.mongo_database import MongoDatabase
from os import getenv

db = MongoDatabase(
        connection_string=getenv(
            'MONGODB_URL', 'mongodb://localhost:27017'),
        database_name='bot_database',
        auto_connect=False
        )