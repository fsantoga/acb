import mysql.connector

def mysqlConenct():
    mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="root",
    database="acb"
    )
    return mydb

