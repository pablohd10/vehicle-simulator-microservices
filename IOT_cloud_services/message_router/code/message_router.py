import time
import threading
import paho.mqtt.client as mqtt
import os
import json
import random

TELEMETRY_TOPIC = "/fic/vehicles/+/telemetry"
PLATE_REQUEST_TOPIC = "/fic/vehicles/+/request_plate"
ROUTE_TOPIC = "/fic/vehicles/{}/routes"
COMPLETED_ROUTE_TOPIC = "/fic/vehicles/+/completed"


connected_vehicles = {}
available_plates = ["0001BBB", "0002BBB", "0003BBB", "0004BBB", "0005BBB",
                    "0006BBB", "0007BBB", "0008BBB", "0009BBB", "0010BBB"]
index_vehicle = 0

pois = [
    "Ayuntamiento de Leganes", "Ayuntamiento de Getafe",
    "Ayuntamiento de Alcorcón", "Ayuntamiento de Móstoles",
    "Universidad Carlos III de Madrid - Campus de Leganés",
    "Universidad Carlos III de Madrid - Campus de Getafe",
    "Universidad Carlos III de Madrid - Campus de Puerta de Toledo",
    "Universidad Carlos III de Madrid - Campus de Colmenarejo",
    "Ayuntamiento de Navalcarnero", "Ayuntamiento de Arroyomolinos",
    "Ayuntamiento de Carranque", "Ayuntamiento de Alcalá de Henares",
    "Ayuntamiento de Guadarrama", "Ayuntamiento de la Cabrera",
    "Ayuntamiento de Aranjuez"
]

def assign_vehicle_info(vehicle_id, plate=None, origin=None, destination=None):
    connected_vehicles[vehicle_id] = {
        "Plate": plate,
        "Route": {
            "Origin": origin,
            "Destination": destination
        }
    }
    return

def send_route(client):
    global connected_vehicles
    global pois
    print("HILO DE ENVÍO DE RUTAS INICIADO")
    while True:
        # Si hay vehículos conectados
        if len(connected_vehicles) > 0:
            print("\nEnviando ruta a un vehículo")
            vehicle_id = random.choice(list(connected_vehicles.keys()))
            print("Vehículo seleccionado: ", vehicle_id)
            # Comprobamos si el vehículo ya tiene una ruta asignada
            current_route = connected_vehicles[vehicle_id]["Route"]
            if current_route["Origin"] == None and current_route["Destination"] == None:
                # Seleccionamos un origen y destino distintos aleatoriamente
                origin = random.choice(pois)
                destination = random.choice([poi for poi in pois if poi != origin])

                route = {"Origin": origin, "Destination": destination}

                # Publicamos la ruta en el topic correspondiente
                topic = ROUTE_TOPIC.format(vehicle_id)
                client.publish(topic, payload=json.dumps(route), qos=1, retain=False)

                # Actualización de la estructura de datos de connected vehicles
                connected_vehicles[vehicle_id]["Route"] = {"Origin": origin, "Destination": destination}
                print("Ruta enviada al vehículo: ", vehicle_id)
                print("Ruta: ", route)
                time.sleep(60)
            else:
                print("El vehículo ya tiene una ruta asignada")
                time.sleep(60)

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

        # Iniciamos un hilo para enviar rutas a los vehículos cada 60 segundos
        t1 = threading.Thread(target=send_route, args=(client,), daemon=True)
        t1.start()
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
        # Comprobamos si el vehículo ya tiene una matrícula asignada
        vehicle = connected_vehicles.get(msg.payload.decode())
        # Si el vehículo ya tiene una matrícula asignada, se le envía la matrícula asignada
        if vehicle:
            print("El vehículo ya tiene una matrícula asignada")
            plate_assigned = vehicle.get("Plate")
            plate_json = {"Plate": plate_assigned}
            # Publicamos la matrícula asignada al vehículo en el topic correspondiente
            client.publish(f"/fic/vehicles/" + str(msg.payload.decode()) + "/config", payload=plate_json, qos=1,
                           retain=False)
            print("Vehículos conectados: ", connected_vehicles)

        # Si el vehículo no tiene una matrícula asignada pero no hay más matrículas disponibles, se le envía un mensaje al vehículo
        elif len(connected_vehicles) >= 10:
            print("La flota de vehículos ya está totalmente asignada")
            client.publish("/fic/vehicles/" + str(msg.payload.decode()) +
                           "/config", payload='{"Plate":"Not Available"}', qos=1,
                           retain=False)
            print("Vehículos conectados: ", connected_vehicles)

        # Si el vehículo no tiene una matrícula asignada y hay matrículas disponibles, se le asigna una matrícula
        else:
            print("Vehículos conectados:", connected_vehicles)
            print("Asignando matrícula al vehículo")
            vehicle_plate = available_plates[index_vehicle]
            assign_vehicle_info(msg.payload.decode(), vehicle_plate)
            print("Matrícula asignada al vehículo: ", vehicle_plate)
            index_vehicle += 1
            plate_json = '{"Plate":"' + vehicle_plate + '"}'
            topic = "/fic/vehicles/" + msg.payload.decode() + "/config"
            print("PUBLICANDO MATRICULA EN EL TOPIC:", topic)
            client.publish("/fic/vehicles/" + msg.payload.decode() + "/config", payload=plate_json, qos=1, retain=False)
            print("Vehículos conectados: ", connected_vehicles)

    # Si el topic es de telemetría
    elif topic[-1] == "telemetry":
        print("Telemetría recibida. Actualizando telemetría")
        # Se actualiza un fichero json local con la nueva telemetría recibida.
        with open('telemetry.json', 'r+') as f:
            # Cargamos el contenido actual del archivo
            current_data = json.load(f)
            # Añadimos la nueva telemetría al final
            current_data.append(json.loads(msg.payload.decode()))
            # Nos movemos al inicio del archivo
            f.seek(0)
            # Escribimos todo de nuevo en el archivo
            json.dump(current_data, f)
        print("Telemetría actualizada")
        with open('telemetry.json', 'r') as f:
            print("Telemetría actual: ", json.load(f))

    elif topic[-1] == "completed":
        print("Ruta completada por parte del vehículo ", topic[-2])
        connected_vehicles[topic[-2]]["Route"]["Origin"] = None
        connected_vehicles[topic[-2]]["Route"]["Destination"] = None
    else:
        print("Topic no reconocido")

if __name__ == '__main__':
    try:
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


