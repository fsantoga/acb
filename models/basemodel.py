import os.path
from peewee import (Model, MySQLDatabase, Proxy)


SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'data.sql'))

SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'initial_sql.sql'))

DB_PROXY = Proxy()
DATABASE = MySQLDatabase("acb",host="localhost", port=3306, user="root", passwd="root")
DB_PROXY.initialize(DATABASE)


def reset_database():
    try:
        DATABASE.close()
    except:
        pass
    with open(SCHEMA_PATH) as f:
        query = f.read()

    try:
        DATABASE.connect()
    except Exception as e:
        print(e)
        try:
            DATABASE.execute_sql(query)
            DATABASE.commit()
        except Exception as e:
            print(e)
    finally:
        DATABASE.close()

def delete_records():
    with open(SCRIPT_PATH) as f:
        query = f.read()
    try:
        DATABASE.connect()
        try:
            DATABASE.execute_sql(query)
            DATABASE.commit()
        except Exception as e:
            print(e)
    except Exception as e:
        print(e)
    finally:
        DATABASE.close()




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
        cursor.close()
        conn.close()
        conn.disconnect()


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
        cursor.close()
        conn.close()
        conn.disconnect()

class BaseModel(Model):
    class Meta:
        database = DB_PROXY
"""