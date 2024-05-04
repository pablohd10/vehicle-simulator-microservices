import requests
import os

def register_vehicle (data):
  host = os.getenv('VEHICLES_MICROSERVICE_ADDRESS')
  port = os.getenv('VEHICLES_MICROSERVICE_PORT')
  r = requests.post('http://' + host + ':' + port + '/vehicles/register', json=data)
  print("Respuesta de la API vehicles/register: ", r)
  return r.json()