
import os.path, logging
from peewee import (Model, MySQLDatabase, Proxy)

SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'mysql_schema.sql'))
SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'initial_sql.sql'))
db = MySQLDatabase("acb2", host="localhost", port=3306, user="root", passwd="root")


def reset_database(logging_level=logging.INFO):

    logging.basicConfig(level=logging_level)
    logger = logging.getLogger(__name__)

    with open(SCHEMA_PATH) as f:
        query = f.read()

    try:
        db.connect()
        try:
            logger.info('Creating Database and Database Schema...\n')
            db.execute_sql(query)
            db.commit()
        except Exception as e:
            print(e)
    except Exception as e:
        print(e)
    finally:
        db.close()


def delete_records(logging_level=logging.INFO):

    logging.basicConfig(level=logging_level)
    logger = logging.getLogger(__name__)

    with open(SCRIPT_PATH) as f:
        query = f.read()
    try:
        db.connect()
        try:
            logger.info('Deleting previous records...')
            logger.info('Set auto_increment=1...\n')
            db.execute_sql(query)
            db.commit()
        except Exception as e:
            print(e)
    except Exception as e:
        print(e)
    finally:
        db.close()

class BaseModel(Model):
    class Meta:
        database = db


"""
import os.path
from peewee import (Model, MySQLDatabase, Proxy)
from src.mysql_connection import *

SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'mysql_schema.sql'))

conn=mysqlConnect()
DB_PROXY = Proxy()
DATABASE = MySQLDatabase("acb",host="localhost", port=3306, user="root", passwd="root")
DB_PROXY.initialize(DATABASE)


def reset_database():
    try:
        conn.close()
    except Exception as e:
        print (e)
        pass
    with open(SCHEMA_PATH) as f:
        query = f.read()

    try:
        cursor=conn.cursor()
        cursor.execute(query)
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        conn.close()

class BaseModel(Model):
    class Meta:
        database = DB_PROXY
"""
