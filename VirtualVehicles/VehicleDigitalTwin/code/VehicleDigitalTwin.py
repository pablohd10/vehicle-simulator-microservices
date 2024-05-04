import time
import json
import os
import threading
import requests
import subprocess
from math import cos, sin, radians, acos
import random
from datetime import datetime
import paho.mqtt.client as mqtt

# Variables globales para almacenar información del vehículo y la ruta
currentRouteDetailedSteps = []
vehicleControlCommands = []
time_to_next_command = 0
comando_actual = True
current_obstacle_distance = 0
current_steering=0
current_speed=0
current_ldr = 0
current_position = {"latitude": 0, "longitude": 0}
# Estado actual de las luces LED del vehículo
current_leds_str = ['{"Color": "White", "Intensity": "0.0", "Blinking": "0"}',
                    '{"Color": "White", "Intensity": "0.0", "Blinking": "0"}',
                    '{"Color": "Red", "Intensity": "0.0", "Blinking": "0"}',
                    '{"Color": "Red", "Intensity": "0.0", "Blinking": "0"}']
parado=False
cambio = False
event_message = ""
vehicle_plate = None

# Función para obtener la ruta entre dos ubicaciones
def routes_manager(origin_address, destination_address):
    global currentRouteDetailedSteps
    global vehicleControlCommands
    # Se genera la URL de la API de Google Maps para obtener la ruta
    url = "https://maps.googleapis.com/maps/api/directions/json?origin=" + origin_address + "&destination=" + destination_address + "&key=" + "AIzaSyDJ2NYAvP6xd9boC0XtSUmaurvNsSymIis"
    # print("URL: {}".format(url))
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    # Se extraen los pasos detallados de la respuesta
    steps = response.json()["routes"][0]["legs"][0]["steps"]

    # Se obtienen los detalles de los pasos y se generan los comandos de control del vehículo
    currentRouteDetailedSteps = get_detailed_steps(steps)
    getCommands(currentRouteDetailedSteps)

# Procesa los pasos detallados de la ruta
def get_detailed_steps(steps):
    detailed_steps = []
    for step in steps:
        # Si la distancia es 0, se omite el paso
        if step["distance"]["value"] == 0:
            continue
        step_speed = (step["distance"]["value"] / 1000) / (step["duration"]["value"] / 3600)
        try:
            step_maneuver = step["maneuver"]
        except:
            step_maneuver = "Straight"
        substeps = decode_polyline(step["polyline"]["points"])
        for index, substep in enumerate(substeps):
            if index < len(substeps) - 1:
                p1 = {"latitude": substep[0], "longitude": substep[1]}
                p2 = {"latitude": substeps[index + 1][0], "longitude": substeps[index + 1][1]}
                points_distance = distance(p1, p2)
                if points_distance > 0.001:
                    substep_duration = points_distance / step_speed
                    new_detailed_step = {
                        "Origin": p1,
                        "Destination": p2,
                        "Speed": step_speed,
                        "Time": substep_duration,
                        "Distance": points_distance,
                        "Maneuver": step_maneuver
                    }
                    detailed_steps.append(new_detailed_step)
    return detailed_steps

# Decodifica una cadena codificada de puntos de una polilínea
def decode_polyline(polyline_str):
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}
    while index < len(polyline_str):
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0
            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)
            lat += changes['latitude']
            lng += changes['longitude']
            coordinates.append((lat / 100000.0, lng / 100000.0))
    return coordinates


# Calcula la distancia entre dos puntos geográficos
def distance(p1, p2):
    p1Latitude = p1["latitude"]
    p1Longitude = p1["longitude"]
    p2Latitude = p2["latitude"]
    p2Longitude = p2["longitude"]
    earth_radius = {"km": 6371.0087714, "mile": 3959}
    # Ajustada para evutar errores
    dot_product = cos(radians(p1Latitude)) * cos(radians(p2Latitude)) * cos(radians(p2Longitude) - radians(p1Longitude)) + sin(radians(p1Latitude)) * sin(radians(p2Latitude))
    dot_product = max(min(dot_product, 1), -1)  # Ajustar a 1 o -1 si es necesario
    result = earth_radius["km"] * acos(dot_product)
    return result

# Genera los comandos de control del vehículo en función de los pasos detallados de la ruta
def getCommands(currentRouteDetailedSteps):
    global vehicleControlCommands
    steeringAngle = 90.0
    vehicleControlCommands = []
    index = 0
    for detailedStep in currentRouteDetailedSteps:
        index += 1
        if (detailedStep["Maneuver"].upper() == "STRAIGHT" or
                detailedStep["Maneuver"].upper() == "RAMP_LEFT" or
                detailedStep["Maneuver"].upper() == "RAMP_RIGHT" or
                detailedStep["Maneuver"].upper() == "MERGE" or
                detailedStep["Maneuver"].upper() == "MANEUVER_UNSPECIFIED"):
            steeringAngle = 90.0
        if detailedStep["Maneuver"].upper() == "TURN_LEFT":
            steeringAngle = 45.0
        if detailedStep["Maneuver"].upper() == "UTURN_LEFT":
            steeringAngle = 0.0
        if detailedStep["Maneuver"].upper() == "TURN_SHARP_LEFT":
            steeringAngle = 15.0
        if detailedStep["Maneuver"].upper() == "TURN_SLIGHT_LEFT":
            steeringAngle = 60.0
        if detailedStep["Maneuver"].upper() == "TURN_RIGHT":
            steeringAngle = 135.0
        if detailedStep["Maneuver"].upper() == "UTURN_RIGHT":
            steeringAngle = 180.0
        if detailedStep["Maneuver"].upper() == "TURN_SHARP_RIGHT":
            steeringAngle = 105.0
        if detailedStep["Maneuver"].upper() == "TURN_SLIGHT_RIGHT":
            steeringAngle = 150.0
        newCommand = {"SteeringAngle": steeringAngle, "Speed": detailedStep["Speed"], "Time": detailedStep["Time"]}
        vehicleControlCommands.append(newCommand)

# Controla la ejecución de los comandos de control del vehículo
def controlar_vehiculo():
    global comando_actual
    global time_to_next_command
    global event_message
    # Thread para actualizar el tiempo que falta para el siguiente comando
    thread_time_to_next_command = threading.Thread(target=actualizar_tiempo_siguiente_comando, args=(), daemon=True)
    thread_time_to_next_command.start()
    # Si no hay comandos de control, esperamos
    while len(vehicleControlCommands) == 0:
        time.sleep(0.1)
    while len(vehicleControlCommands)>0:
        # Si el comando anterior ha terminado, obtenemos el siguiente comando
        if time_to_next_command <= 0.000000000000:
            try:
                comando_actual = vehicleControlCommands.pop(0)
                step_actual = currentRouteDetailedSteps.pop(0)
                time_to_next_command = comando_actual['Time']
                execute_command(comando_actual,step_actual)
            except:
                vehicle_stop()
    print("Has llegado al destino. Ruta completada.")
    event_message = "Route Completed"
    return

# Función para actualizar el tiempo restante para el siguiente comando
def actualizar_tiempo_siguiente_comando():
    global time_to_next_command
    global comando_actual
    global parado
    global cambio
    global current_speed
    while comando_actual:
        print("\nTiempo restante para el siguiente comando:", time_to_next_command, "segundos")
        print("Angulo: ", current_steering)
        print("Luminosidad: ",current_ldr)
        if current_obstacle_distance<=0:
            print("Distancia obstaculo: 0")
        else:
            print("Distancia obstaculo: ",current_obstacle_distance)
        if not parado:
            if time_to_next_command > 0.0:
                time_to_next_command -= 10
            # Cambio de velocidad
            if cambio==True:
                cambio=False
                current_speed = guardar_velocidad
        else:
            guardar_velocidad = current_speed
            current_speed = 0
            cambio = True
        print("Speed: ", current_speed)
        print(current_leds_str[0])
        print(current_leds_str[1])
        print(current_leds_str[2])
        print(current_leds_str[3])
        time.sleep(30)
    return

# Ejecuta un comando de control del vehículo
def execute_command(command,step):
    global current_steering
    global current_speed
    global current_position
    current_steering = command["SteeringAngle"]
    current_speed = command["Speed"]
    current_position = step["Destination"]
    while (time_to_next_command)>0.0:
        time.sleep(0.25)

# Simula el entorno del vehículo, como la lectura de sensores de luz y distancia al obstáculo
def environment_simulator():
    global current_ldr
    global current_obstacle_distance
    global parado
    while comando_actual:
        if current_ldr > 0.0:
            # Simular la luz
            random_luminosity = random.randint(-300, 300)
            current_ldr += random_luminosity
        else:
            current_ldr = random.uniform(0.0, 3000.0)

        if current_obstacle_distance > 0.0:
            # Simular la distancia al obstáculo
            random_distance = random.randint(-5, 5)
            current_obstacle_distance += random_distance
        else:
            current_obstacle_distance = random.uniform(0.0, 50.0)

        if current_obstacle_distance < 10:
            parado=True
        else:
            parado=False
        time.sleep(1)


# Controla las luces LED del vehículo en función de las condiciones del entorno y el estado del vehículo
def led_controller():
    global current_ldr
    global current_steering
    global parado
    global comando_actual
    while comando_actual:
        # Intermitencia
        if current_steering > 100:
            current_leds_str[0] = '{"Color": "Yellow", "Intensity": "1.0," "Blinking": "1"}'
            current_leds_str[2] = '{"Color": "Red", "Intensity": "1.0", "Blinking": "1"}'
        elif current_steering < 80:
            current_leds_str[1] = '{"Color": "Yellow", "Intensity": "1.0", "Blinking": "1"}'
            current_leds_str[3] = '{"Color": "Red", "Intensity": "1.0", "Blinking": "1"}'
        # Luces de freno
        elif parado:
            current_leds_str[2] = '{"Color": "Red", "Intensity": "1.0", "Blinking": "0"}'
            current_leds_str[3] = '{"Color": "Red", "Intensity": "1.0", "Blinking": "0"}'
        # Luces de posición
        elif current_ldr > 3000:
            current_leds_str[0] = '{"Color": "White", "Intensity": "1.0", "Blinking": "0"}'
            current_leds_str[1] = '{"Color": "White", "Intensity": "1.0", "Blinking": "0"}'
            current_leds_str[2] = '{"Color": "Red", "Intensity": "0.5", "Blinking": "0"}'
            current_leds_str[3] = '{"Color": "Red", "Intensity": "0.5", "Blinking": "0"}'
        # Luces apagadas cuando hay suficiente luminosidad
        elif current_ldr < 3000:
            current_leds_str[0] = '{"Color": "White", "Intensity": "0.0", "Blinking": "0"}'
            current_leds_str[1] = '{"Color": "White", "Intensity": "0.0", "Blinking": "0"}'
            current_leds_str[2] = '{"Color": "Red", "Intensity": "0.0", "Blinking": "0"}'
            current_leds_str[3] = '{"Color": "Red", "Intensity": "0.0", "Blinking": "0"}'
    return

def vehicle_stop():
    global vehicleControlCommands
    global currentRouteDetailedSteps
    global current_steering
    global current_speed
    global current_leds_str
    global current_ldr
    global current_obstacle_distance

    vehicleControlCommands = []
    currentRouteDetailedSteps = []
    current_steering = 90.0
    current_speed = 0

    current_leds_str = ['LUZ DELANTERA IZQUIERDA {"Color": "White", "Intensity": "0.0", "Blinking": "0"}',
                        'LUZ DELANTERA DERECHA {"Color": "White", "Intensity": "0.0", "Blinking": "0"}',
                        'LUZ TRASERA IZQUIERDA {"Color": "Red",   "Intensity": "0.0",   Blinking: "0"}',
                        'LUZ TRASERA DERECHA {"Color": "Red", "Intensity": "0.0", "Blinking": "0"}']
    current_ldr = 0.0
    current_obstacle_distance = 0.0

def mqtt_communications():
    global vehicle_plate
    global TELEMETRY_TOPIC
    global PLATE_REQUEST_TOPIC
    global CONFIG_TOPIC
    global ROUTES_TOPIC
    global COMPLETED_ROUTE_TOPIC
    TELEMETRY_TOPIC = "/fic/vehicles/" + get_host_name() + "/telemetry"
    PLATE_REQUEST_TOPIC = "/fic/vehicles/" + get_host_name() + "/request_plate"
    CONFIG_TOPIC = "/fic/vehicles/" + get_host_name() + "/config"
    ROUTES_TOPIC = "/fic/vehicles/" + get_host_name() + "/routes"
    COMPLETED_ROUTE_TOPIC = "/fic/vehicles/" + get_host_name() + "/completed"

    client = mqtt.Client()
    client.username_pw_set(username="fic_server", password="fic_password")
    client.on_connect = on_connect
    client.on_message = on_message

    # Se establece un mensaje que se enviará si el vehiculo se desconecta inesperadamente.
    connection_dict = {"vehicle_plate": vehicle_plate, "status":
                       "Off - Unregular Diconnection",
                       "timestamp": datetime.now().isoformat()}
    connection_str = json.dumps(connection_dict)
    client.will_set(TELEMETRY_TOPIC, connection_str)

    MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS")
    MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT"))
    client.connect(MQTT_SERVER, MQTT_PORT, 60)
    client.loop_forever()

def publish_telemetry(client):
    print("HILO DE PUBLICACIÓN DE TELEMETRÍA INICIADO")
    # Este hilo estará siempre publicando la telemetría del vehículo en caso de que el vehículo tenga una matrícula asignada
    while True:
        if vehicle_plate:
            # Obtener el estado del vehículo
            vehicle_status = {
                "id": get_host_name(),
                "vehicle_plate": vehicle_plate,
                "telemetry": {
                    "current_steering": current_steering,
                    "current_speed": current_speed,
                    "current_position": current_position,
                    "current_leds": current_leds_str,
                    "current_ldr": current_ldr,
                    "current_obstacle_distance": current_obstacle_distance,
                    "time_stamp": datetime.now().isoformat()
                }
            }

            # Publicar el estado del vehículo
            json_telemetry = json.dumps(vehicle_status)
            print("\nPublicando telemetría del vehículo")
            client.publish(TELEMETRY_TOPIC, payload=json_telemetry, qos=1, retain=False)
            time.sleep(30)

def check_if_route_completed(client):
    print("HILO DE COMPROBACIÓN DE RUTA COMPLETADA INICIADO")
    global event_message
    while True:
        if event_message != "":
            event_to_send = {"Plate": vehicle_plate, "Event": event_message,
                             "Timestamp": datetime.timestamp(datetime.now())}
            client.publish(COMPLETED_ROUTE_TOPIC, payload=json.dumps(event_to_send), qos=1,
                           retain=False)
            event_message = ""

def on_connect(client, userdata, flags, rc):
    print("Código de resultado de la conexión: ", rc)
    if rc == 0:
        # Se imprime un mensaje de confirmación de conexión
        print("Conexión exitosa al broker MQTT")

        client.subscribe(CONFIG_TOPIC)
        print("Suscrito al topic:", CONFIG_TOPIC)
        client.subscribe(ROUTES_TOPIC)
        print("Suscrito al topic:", ROUTES_TOPIC)

        # Se publica en el topic de solicitud de matrícula el identificador del vehículo
        client.publish(PLATE_REQUEST_TOPIC, payload=get_host_name(), qos=1, retain=False)
        print("Mensaje de solicitud de matrícula publicado en el topic:", PLATE_REQUEST_TOPIC)

        # Se inicia un thread para publicar la telemetría del vehículo
        thread_publish_telemetry = threading.Thread(target=publish_telemetry, args=(client,), daemon=True)
        thread_publish_telemetry.start()

        # Se inicia un thread para comprobar si se ha completado la ruta
        thread_check_if_route_completed = threading.Thread(target=check_if_route_completed, args=(client,), daemon=True)
        thread_check_if_route_completed.start()
    else:
        print("Conexión fallida al broker MQTT")

def get_host_name():
    # Se obtiene el nombre del host ejecutando un comando bash
    bash_command = "echo $HOSTNAME"
    host = subprocess.check_output(['bash', '-c', bash_command]).decode('utf-8')[0:-1]
    return host

def on_message(client, userdata, msg):
    global vehicle_plate
    print("\nMensaje recibido desde el broker MQTT")
    print("Topic: ", msg.topic)
    print("Mensaje: ", msg.payload.decode())
    print("QoS: ", msg.qos)

    topic = (msg.topic).split('/')
    if topic[-1] == "config":
        # Se actualiza el diccionario con la información de la matrícula asignada al vehículo
        config_received = msg.payload.decode()
        json_config_received = json.loads(config_received) # Se convierte el mensaje a un json
        if json_config_received["Plate"] != "Not Available":
            vehicle_plate = json_config_received["Plate"]
            print("Matrícula asignada al vehículo: ", vehicle_plate)
        else:
            print("No hay matrículas disponibles para asignar al vehículo")
    elif topic[-1] == "routes":
        required_route = json.loads(msg.payload.decode())
        print("Ruta requerida: ", required_route)
        origin = required_route["Origin"]
        destination = required_route["Destination"]
        routes_manager(origin, destination)

if __name__ == '__main__':
     try:
         # print(vehicleControlCommands)
         t1 = threading.Thread(target=mqtt_communications, daemon=True)
         t1.start()
         t2 = threading.Thread(target=environment_simulator,daemon=True)
         t2.start()
         t3 = threading.Thread(target=controlar_vehiculo, daemon=True)
         t3.start()
         t4 = threading.Thread(target=led_controller, daemon=True)
         t4.start()
         t1.join()
         t2.join()
         t3.join()
         t4.join()

     except Exception as e:
         print(e)
         vehicle_stop()

