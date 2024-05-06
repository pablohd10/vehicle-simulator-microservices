import threading
import paho.mqtt.client as mqtt
import os
import json
from telemetry_register_interface import register_telemetry
from vehicle_register_interface import register_vehicle
from flask import Flask, request
from flask_cors import CORS

TELEMETRY_TOPIC = "/fic/vehicles/+/telemetry"
PLATE_REQUEST_TOPIC = "/fic/vehicles/+/request_plate"
ROUTE_TOPIC = "/fic/vehicles/{}/routes"
COMPLETED_ROUTE_TOPIC = "/fic/vehicles/+/completed"


connected_vehicles = {}
available_plates = ["0001BBB", "0002BBB", "0003BBB", "0004BBB", "0005BBB",
                    "0006BBB", "0007BBB", "0008BBB", "0009BBB", "0010BBB"]
index_vehicle = 0

def assign_vehicle_info(vehicle_id, plate=None, origin=None, destination=None):
    connected_vehicles[vehicle_id] = {
        "Plate": plate,
        "Route": {
            "Origin": origin,
            "Destination": destination
        }
    }
    print("Vehículos conectados: ", connected_vehicles)
    return

def get_vehicle_id_by_plate(plate):
    for vehicle_id, vehicle_info in connected_vehicles.items():
        if vehicle_info['Plate'] == plate:
            return vehicle_id
    return None

def on_connect(client, userdata, flags, rc):
    global TELEMETRY_TOPIC
    global PLATE_REQUEST_TOPIC

    print("Resultado de la conexión con el broker: ", str(rc))

    # Nos suscribimos a los topics de los vehículos
    if rc == 0:
        print("Conexión establecida exitosamente")
        client.subscribe(TELEMETRY_TOPIC)
        print("Subscribed to", TELEMETRY_TOPIC)
        client.subscribe(COMPLETED_ROUTE_TOPIC)
        print("Subscribed to", COMPLETED_ROUTE_TOPIC)
        # Creamos un archivo json para almacenar la telemetría
        data = []
        with open('telemetry.json', 'w') as f:
            json.dump(data, f)
        client.subscribe(PLATE_REQUEST_TOPIC)
        print("Subscribed to", PLATE_REQUEST_TOPIC)

    else:
        print("Error de conexión")

def on_message(client, userdata, msg):
    global connected_vehicles
    global available_plates
    global index_vehicle

    print("\nMensaje recibido")
    # Imprimimos por pantalla el mensaje recibido
    print("Topic: ", msg.topic)
    print("Mensaje: ", msg.payload.decode())
    print("QoS: ", msg.qos) # Quality of Service

    topic = (msg.topic).split("/")

    # Si el topic es de asignación de matrícula
    if topic[-1] == "request_plate":
        input_data = msg.payload.decode()
        request_data = {"vehicle_id": input_data}
        # Petición HTTP a la API del microservicio de vehículos para registrar un nuevo vehículo
        print("Petición HTTP a la API de vehículos para registrar un vehículo")
        vehicle_plate = register_vehicle(request_data)

        assign_vehicle_info(input_data, vehicle_plate["Plate"])

        vehicle_plate_str = json.dumps(vehicle_plate)  # Convertimos el diccionario a un string JSON
        client.publish("/fic/vehicles/" + msg.payload.decode() + "/config", payload=vehicle_plate_str, qos=1, retain=False)
        print("Publicado", vehicle_plate, "en TOPIC", msg.topic)

    # Si el topic es de telemetría
    elif topic[-1] == "telemetry":
        print("Telemetría recibida. Actualizando telemetría")
        str_received_telemetry = msg.payload.decode()
        received_telemetry = json.loads(str_received_telemetry)
        result = register_telemetry(received_telemetry)
        print(result)

    elif topic[-1] == "completed":
        print("Ruta completada por parte del vehículo ", topic[-2])
        connected_vehicles[topic[-2]]["Route"]["Origin"] = None
        connected_vehicles[topic[-2]]["Route"]["Destination"] = None
    else:
        print("Topic no reconocido")

def mqtt_communications():
    try:
        global client
        client = mqtt.Client() # Creamos un cliente MQTT
        client.username_pw_set(username="fic_server", password="fic_password") # Configuramos el usuario y contraseña
        # Establecemos cuáles son los métodos de callback para los eventos on_connect y on_message
        client.on_connect = on_connect
        client.on_message = on_message

        MQTT_SERVER = os.getenv("MQTT_SERVER_ADDRESS") # Obtenemos la dirección del servidor MQTT
        MQTT_PORT = int(os.getenv("MQTT_SERVER_PORT")) # Obtenemos el puerto del servidor MQTT
        client.connect(MQTT_SERVER, MQTT_PORT, 60) # Nos conectamos al servidor MQTT

        # Configuramos el cliente para que esté recibiendo constantemente comunicaciones del mosquitto
        client.loop_forever()
    finally:
        client.disconnect()
        return

if __name__ == '__main__':
    global client
    t1 = threading.Thread(target=mqtt_communications, daemon=True)
    t1.start()

    app = Flask(__name__)
    CORS(app)

    @app.route('/routes/send', methods=['POST'])
    def send_route():
        """
        Send a route to a vehicle.
        :parameter plate: The plate of the vehicle to assign the route.
        :parameter origin: The origin of the route.
        :parameter destination: The destination of the route.
        example:
        {
            "plate": "1234BBC",
            "origin": "Navalcarnero",
            "destination": "Carranque"
        }
        :return: A JSON object with the result of the operation.
        """
        params = request.get_json()
        # Obtenemos los parámetros de la petición (matrícula, origen y destino)
        plate = params["plate"]
        origin = params["origin"]
        destination = params["destination"]
        route = {"Origin": origin, "Destination": destination}

        print("Vehículo con matrícula ", plate, " solicitando ruta")

        # Comprobamos si el vehículo está conectado
        vehicle_id = get_vehicle_id_by_plate(plate)
        print("Vehicle ID: ", vehicle_id)
        print("Connected vehicles: ", connected_vehicles)
        if vehicle_id is None:
            return {"result": "Vehicle is not connected"}, 500

        # Publicamos la ruta en el topic correspondiente
        vehicle_route_topic = ROUTE_TOPIC.format(vehicle_id)
        client.publish(vehicle_route_topic, payload=json.dumps(route), qos=1, retain=False)
        print("Ruta enviada al vehículo ", vehicle_id)
        # Actualizamos la estructura de datos de connected vehicles
        assign_vehicle_info(vehicle_id, plate, origin, destination)
        return {"result": "Route successfully sent"}, 201

    HOST = os.getenv("HOST")
    PORT = os.getenv("PORT")
    app.run(HOST, PORT, debug=True)

    t1.join() # Esperamos a que el hilo termine


