"""
import os.path
from peewee import (Model, SqliteDatabase, Proxy)

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                       '..', 'data', 'database.db'))
SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'schema.sql'))
DB_PROXY = Proxy()
DATABASE = SqliteDatabase(DB_PATH)
DB_PROXY.initialize(DATABASE)


def reset_database():
    try:
        DATABASE.close()
    except:
        pass
    try:
        os.remove(DB_PATH)
    except FileNotFoundError:
        pass
    with open(SCHEMA_PATH) as f:
        query = f.read()


    c =DATABASE.cursor()
    c.executescript(query)
    DATABASE.commit()
    DATABASE.close()

    #DATABASE.init(DB_PATH)
    #DATABASE.connect()
    #DATABASE.execute("CREATE TABLE team (id INTEGER PRIMARY KEY, acbid TEXT UNIQUE NOT NULL, founded_year INTEGER);")

class BaseModel(Model):
    class Meta:
        database = DB_PROXY


"""
import os.path
from peewee import (Model, MySQLDatabase, Proxy)
from src.mysql_connection import *

SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'data.sql'))
SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'initial_sql.sql'))

DB_PROXY = Proxy()
DATABASE = MySQLDatabase("acb",host="localhost", port=3306, user="root", passwd="root")
DB_PROXY.initialize(DATABASE)


def reset_database():
    conn = mysqlConenct()
    with open(SCHEMA_PATH) as f:
        query = f.read()

    try:
        cursor=conn.cursor()
        cursor.execute(query,multi=True)
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        conn.close()


def delete_records():
    conn = mysqlConenct()
    with open(SCRIPT_PATH) as f:
        query = f.read()
    try:
        cursor = conn.cursor()
        cursor.execute(query,multi=True)
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        conn.close()

class BaseModel(Model):
    class Meta:
        database = DB_PROXY
