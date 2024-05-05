import requests
import os

def register_telemetry(data):
  host = os.getenv('TELEMETRY_MICROSERVICE_ADDRESS')
  port = os.getenv('TELEMETRY_MICROSERVICE_PORT')
  r = requests.post('http://' + host + ':' + port + '/telemetry/register', json=data)
  print("Respuesta de la API telemetry/register: ", r.json(), r.status_code)
  return r.json()