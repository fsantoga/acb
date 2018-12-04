import pymysql

def mysqlConnect():
    conn = pymysql.connect(host='localhost',
                           user='root',
                           password='root')
    return conn

