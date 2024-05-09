from flask import Flask, request
from flask_cors import CORS
from routes_db_manager import *
import requests

app = Flask(__name__)
CORS(app)

@app.route('/routes/assign', methods=['POST'])
def assign_route():
    """
    Assign a route to a vehicle. The route is defined by its origin and destination.
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
    plate = params["plate"]
    origin = params["origin"]
    destination = params["destination"]
    if assign_new_route_db(plate, origin, destination):
        host = os.getenv('MESSAGE_ROUTER_ADDRESS')
        port = os.getenv('MESSAGE_ROUTER_PORT')
        data = {"plate": plate, "origin": origin, "destination": destination}
        r = requests.post('http://' + host + ':' + port + '/routes/send', json=data)
        response = r.dumps()
        print("Respuesta de la API del message router routes/send: ", response.json(), r.status_code)
        return response, 201
    else:
        return {"result": "Error assigning a new route"}, 500

@app.route('/routes/retrieve', methods = ['GET'])
def retrieve_routes():
    """
    Retrieve the routes assigned to a specific vehicle.
    :parameter plate: The plate of the vehicle to retrieve the routes.
    example:
    {
        "plate": "34521BBC"
    }
    :return: A JSON objects with the routes assigned to the vehicles and an error message if there is any.
    """
    params = request.get_json()
    routes = get_routes_assigned_to_vehicle_db(params["plate"])
    if routes["Error Message"] is None:
        return routes, 201
    else:
        return routes, 500

HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
app.run(HOST, PORT)