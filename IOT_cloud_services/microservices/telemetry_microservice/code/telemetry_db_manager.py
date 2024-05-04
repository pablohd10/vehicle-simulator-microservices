import mysql.connector
import os

def connect_database():
    # Nos conectamos a la base de datos
    mydb = mysql.connector.connect(
        host=os.getenv("DBHOST", "127.0.0.1"),
        user=os.getenv("DBUSER", "fic_db_user"),
        password=os.getenv("DBPASSWORD", "RP#64nY7*E*H"),
        database=os.getenv("DBDATABASE", "fic_data")
    )
    return mydb

def register_new_telemetry(params):
    mydb = connect_database()
    mycursor = mydb.cursor()
    sql = "INSERT INTO vehicles_telemetry (vehicle_id, current_steering, current_speed, latitude, longitude, current_ldr, current_obstacle_distance, front_left_led_intensity, front_right_led_intensity, rear_left_led_intensity, rear_right_led_intensity, front_left_led_color, front_right_led_color, rear_left_led_color, rear_right_led_color, front_left_led_blinking, front_right_led_blinking, rear_left_led_blinking, rear_right_led_blinking, time_stamp) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"
    val = (params['vehicle_id'], params['current_steering'], params['current_speed'], params['current_position']['Latitude'], params['current_position']['Longitude'], params['current_ldr'], params['current_obstacle_distance'], params['current_leds'][0]['Intensity'], params['current_leds'][1]['Intensity'], params['current_leds'][2]['Intensity'], params['current_leds'][3]['Intensity'], params['current_leds'][0]['Color'], params['current_leds'][1]['Color'], params['current_leds'][2]['Color'], params['current_leds'][3]['Color'], params['current_leds'][0]['Blinking'], params['current_leds'][1]['Blinking'], params['current_leds'][2]['Blinking'], params['current_leds'][3]['Blinking'], params['time_stamp'])
    try:
        mycursor.execute(sql, val)
        mydb.commit()
        return True
    except Exception as e:
        print("Error registering telemetry:", e)
        return False

def get_vehicle_detailed_info(vehicle_id):
    mydb = connect_database()
    mycursor = mydb.cursor(dictionary=True)
    sql = "SELECT vehicle_id, current_steering, current_speed, latitude, longitude, current_ldr, current_obstacle_distance, front_left_led_intensity, front_right_led_intensity, rear_left_led_intensity, rear_right_led_intensity, front_left_led_color, front_right_led_color, rear_left_led_color, rear_right_led_color, front_left_led_blinking, front_right_led_blinking, rear_left_led_blinking, rear_right_led_blinking, time_stamp FROM vehicles_telemetry WHERE vehicle_id = %s ORDER BY time_stamp LIMIT 20;"
    query_params = (vehicle_id, )
    try:
        mycursor.execute(sql, query_params)
        myresult = mycursor.fetchall()
        result = {"telemetries": myresult, "Error Message": None}
        return result
    except Exception as e:
        error_message = {"Error Message": e}
        return error_message

def get_active_vehicles_last_position():
    mydb = connect_database()
    mycursor = mydb.cursor(dictionary=True)
    print("Obteniendo posiciones de los vehículos activos")
    sql = "SELECT v.plate, vt.latitude, vt.longitude, vt.time_stamp FROM vehicles v JOIN vehicles_telemetry vt ON v.vehicle_id = vt.vehicle_id WHERE v.status = 1 AND vt.time_stamp = (SELECT MAX(time_stamp) FROM vehicles_telemetry WHERE vehicle_id = v.vehicle_id);"
    print("Ejecutando la consulta")
    print(sql)
    try:
        mycursor.execute(sql)
        myresult = mycursor.fetchall()
        print(myresult)
        result = {"Positions": myresult, "Error Message": None}
        return result
    except Exception as e:
        error_message = {"Error Message": e}
        return error_message