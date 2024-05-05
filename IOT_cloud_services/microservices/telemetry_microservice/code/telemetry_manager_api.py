from flask import Flask, request
from flask_cors import CORS
from telemetry_db_manager import *

app = Flask(__name__)
CORS(app)

@app.route('/telemetry/register', methods=['POST'])
def register_telemetry():
    params = request.get_json()
    if register_new_telemetry(params):
        print("Telemetry registered")
        return {"result": "Telemetry registered"}, 201
    else:
        return {"result": "Error registering telemetry"}, 500

@app.route('/telemetry/vehicle/detailed_info', methods=['GET'])
def retrieve_vehicle_detailed_info():
    params = request.get_json()
    vehicle_id = params["vehicle_id"]
    vehicle_info = get_vehicle_detailed_info(vehicle_id)
    if vehicle_info["Error Message"] is None:
        return vehicle_info, 201
    else:
        return vehicle_info, 500

@app.route('/telemetry/vehicle/positions', methods=['GET'])
def retrieve_vehicles_positions():
    positions = get_active_vehicles_last_position()
    if positions["Error Message"] is None:
        return positions, 201
    else:
        return positions, 500


HOST = os.getenv("HOST")
PORT = os.getenv("PORT")
app.run(HOST, PORT)