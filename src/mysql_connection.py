import mysql.connector


def mysqlConnect():
    mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="root",
    database="acb"
    )
    return mydb

