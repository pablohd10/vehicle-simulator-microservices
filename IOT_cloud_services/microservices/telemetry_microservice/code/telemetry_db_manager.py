import mysql.connector
import os

def connect_to_db():
    # Nos conectamos a la base de datos
    mydb = mysql.connector.connect(
        host=os.getenv("DBHOST"),
        user=os.getenv("DBUSER"),
        password=os.getenv("DBPASSWORD", "RP#64nY7*E*H" ),
        database=os.getenv("DBDATABASE", "fic_data")
    )
    return mydb
