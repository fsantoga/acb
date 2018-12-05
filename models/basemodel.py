import os.path, logging
from peewee import (Model, MySQLDatabase, Proxy)
import sqlparse
import pymysql

SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'mysql_schema.sql'))
SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'initial_sql.sql'))
db = MySQLDatabase("acb", host="localhost", port=3306, user="root", passwd="root")


def reset_database(logging_level=logging.INFO):

    logging.basicConfig(level=logging_level)
    logger = logging.getLogger(__name__)

    try:
        conn=pymysql.connect(host="localhost", port=3306, user="root", passwd="root")
        cursor=conn.cursor()
        try:
            logger.info('Creating Database...\n')
            cursor.execute("DROP DATABASE IF EXISTS acb;")
            cursor.execute("CREATE DATABASE acb;")
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(e)
            conn.rollback()
    except Exception as e:
        print(e)



def create_schema(logging_level=logging.INFO):

    logging.basicConfig(level=logging_level)
    logger = logging.getLogger(__name__)

    with open(SCHEMA_PATH,'rb') as f:
        query = f.read()

    try:
        db.connect()
        logger.info('Creating Database Schema...\n')
        for statement in sqlparse.split(query):
            if not statement:
                continue
            db.execute_sql(statement)
        db.commit()
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
            for statement in sqlparse.split(query):
                if not statement:
                    continue
                db.execute_sql(statement)
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