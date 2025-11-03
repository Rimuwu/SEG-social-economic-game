from global_modules.db.mongo_database import MongoDatabase
from os import getenv

just_db = MongoDatabase(
            connection_string=getenv(
                'MONGODB_URL', 'mongodb://localhost:27017'
            ),
            database_name='api_database',
            auto_connect=True
            )