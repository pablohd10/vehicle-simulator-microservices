# Utiliza la imagen base de Python 3.11.1
FROM python:3.11.1

# Establece el directorio de trabajo en /usr/src/app
WORKDIR /etc/usr/src/app

# Copia el código desde la carpeta local ./code a /usr/src/app en el contenedor
COPY ./code /etc/usr/src/app

# Instala los paquetes necesarios especificados en requirements.txt
RUN pip install -r requirements.txt

# Ejecuta el código incluido en el archivo VehicleDigitalTwin.py
CMD ["python", "VehicleDigitalTwin.py"]