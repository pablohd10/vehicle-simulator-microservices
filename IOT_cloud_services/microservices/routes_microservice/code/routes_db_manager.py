import mysql.connector
import os
from datetime import datetime

def connect_database():
    try:
        mydb = mysql.connector.connect(
            host=os.getenv("DBHOST"),
            user=os.getenv("DBUSER"),
            password=os.getenv("DBPASSWORD"),
            database=os.getenv("DBDATABASE")
        )
        return mydb
    except Exception as e:
        print("Error de conexión a la base de datos: ", e)
        return None

def assign_new_route_db(plate, origin, destination):
    mydb = connect_database()
    if mydb is None:
        return False
    mycursor = mydb.cursor()
    sql = "INSERT INTO routes (plate, origin, destination, time_stamp) VALUES (%s, %s, %s, %s);"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    val = (plate, origin, destination, timestamp)
    try:
        print("Asignando nueva ruta")
        mycursor.execute(sql, val)
        mydb.commit()
        print("Ruta asignada correctamente")
        return True
    except Exception as e:
        print("Error assigning new route:", e)
        mydb.rollback()
        return False


def get_routes_assigned_to_vehicle_db(plate):
    mydb = connect_database()
    mycursor = mydb.cursor()
    sql = "SELECT origin, destination, time_stamp FROM routes WHERE plate = %s;"
    query_params = (plate,)
    try:
        print("Obteniendo rutas asignadas al vehículo")
        mycursor.execute(sql, query_params)
        myresult = mycursor.fetchall()
        result = {"routes": myresult, "Error Message": None}
        print("Rutas obtenidas correctamente", result)
        return result
    except Exception as e:
        print("Error retrieving routes assigned to vehicle:", e)
        error_message = {"Error Message": e}
        return error_message

def delete_last_route():
    mydb = connect_database()
    if mydb is None:
        return False

    mycursor = mydb.cursor()

    # Obtener el ID de la última ruta insertada
    try:
        mycursor.execute("SELECT MAX(id) FROM routes;")
        last_route_id = mycursor.fetchone()[0]
        if last_route_id is None:
            print("No hay rutas en la base de datos")
            return False
    except Exception as e:
        print("Error al obtener el ID de la última ruta:", e)
        return False

    # Eliminar la última ruta
    try:
        sql = "DELETE FROM routes WHERE id = %s;"
        mycursor.execute(sql, (last_route_id,))
        mydb.commit()
        print("Última ruta eliminada correctamente")
        return True
    except Exception as e:
        print("Error al eliminar la última ruta:", e)
        mydb.rollback()
        return False