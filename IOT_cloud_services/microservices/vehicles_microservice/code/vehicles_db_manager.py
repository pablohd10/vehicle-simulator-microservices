import mysql.connector
import os

def connect_to_db():
    # Nos conectamos a la base de datos
    mydb = mysql.connector.connect(
        host=os.getenv("DBHOST"),
        user=os.getenv("DBUSER"),
        password=os.getenv("DBPASSWORD"),
        database=os.getenv("DBDATABASE")
    )
    return mydb

def register_vehicle_db(params):
    vehicle_plate = ""
    mydb = connect_to_db()

    sql_check_plate_assigned = "SELECT plate FROM vehicles WHERE vehicle_id = %s ORDER BY plate ASC LIMIT 1;"
    with mydb.cursor() as mycursor:
        mycursor.execute(sql_check_plate_assigned, (params["vehicle_id"],))
        plate_assigned = mycursor.fetchall()
        for plate in plate_assigned:
            vehicle_plate = plate[0]
        mydb.commit()
    if vehicle_plate != "":
        print("\nEl vehículo ya tiene una matrícula asignada")
        return vehicle_plate
    else:
        print("\nEl vehículo no tiene una matrícula asignada")
        print("Obteniendo matrícula disponible")
        sql_obtain_available_plate = "SELECT plate, is_assigned FROM available_plates WHERE is_assigned = 0 ORDER BY plate ASC LIMIT 1;"
        with mydb.cursor() as mycursor:
            mycursor.execute(sql_obtain_available_plate)
            plate = mycursor.fetchall()
            for plate in plate:
                vehicle_plate = plate[0]
            mydb.commit()

        if vehicle_plate != "":
            print("Matrícula disponible obtenida")
            sql_insert_vehicle = "INSERT INTO vehicles (vehicle_id, plate) VALUES (%s, %s);"
            with mydb.cursor() as mycursor:
                try:
                    mycursor.execute(sql_insert_vehicle, (params["vehicle_id"], vehicle_plate))
                    mydb.commit()
                    sql_update_plate_assigned = "UPDATE available_plates SET is_assigned = 1 WHERE plate = %s;"
                    sql_updtate_vehicle_status = "UPDATE vehicles SET status = 1 WHERE plate = %s;"
                    mycursor.execute(sql_update_plate_assigned, (vehicle_plate,))
                    mycursor.execute(sql_updtate_vehicle_status, (vehicle_plate,))
                    mydb.commit()
                    print(mycursor.rowcount, "record inserted.")
                    print("Matrícula asignada al vehículo: ", vehicle_plate)
                    return vehicle_plate
                except Exception as e:
                    mydb.rollback()
                    print("Error inserting a new vehicle in the db: ", e)
                    return ""
        else:
            print("No hay matrículas disponibles")
            return ""

def get_active_vehicles_db():
    mydb = connect_to_db()
    plates = []
    sql_get_active_vehicles = "SELECT plate FROM vehicles WHERE status = 1 ORDER BY plate;"
    with mydb.cursor() as mycursor:
        mycursor.execute(sql_get_active_vehicles)
        vehicles_db = mycursor.fetchall()
        for plate in vehicles_db:
            data = {"Plate": plate}
            plates.append(data)
        mydb.commit()
    return plates

