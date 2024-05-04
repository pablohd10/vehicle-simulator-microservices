from flask import Flask, request
from flask_cors import CORS
from vehicles_db_manager import *

app = Flask(__name__)
CORS(app)

@app.route('/vehicles/register', methods=['POST'])
def register_vehicle():
    params = request.get_json()
    plate = register_vehicle_db(params)
    if plate is not "":
        return {"Plate": plate}, 201
    else:
        return {"result": "error inserting a new vehicle in the db"}, 500

@app.route('/vehicles/retrieve', methods=['GET'])
def retrieve_vehicles():
    vehicles = get_active_vehicles_db()
    return {"Vehicles": vehicles}, 200

HOST = os.getenv("VEHICLES_MICROSERVICE_ADDRESS")
PORT = os.getenv("VEHICLES_MICROSERVICE_PORT")
app.run(HOST, PORT)