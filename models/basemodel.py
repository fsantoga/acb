
import os.path
from peewee import (Model, MySQLDatabase, Proxy)
import pymysql

SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'mysql_schema.sql'))

db = MySQLDatabase("acb", host="localhost", port=3306, user="root", passwd="root")

def reset_database():

    # Create database
    conn = pymysql.connect(host='localhost',
                           user='root',
                           password='root')

    conn.cursor().execute('DROP DATABASE IF EXISTS acb;')
    conn.cursor().execute('CREATE DATABASE acb;')
    conn.close()


    with open(SCHEMA_PATH) as f:
        script = f.read()
        db.connect(reuse_if_open=True)
        for statement in script.split(';'):
            if len(statement) > 0:
                db.execute_sql(statement + ';')
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
