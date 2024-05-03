# Usar debian:buster como imagen base
FROM debian:buster

# Actualizar el sistema e instalar mosquitto y mosquitto-clients
RUN apt update && apt upgrade -y && apt install mosquitto mosquitto-clients -y

# Crear el archivo de contraseñas de mosquitto
RUN touch /etc/mosquitto/passwd

# Establecer la contraseña para el usuario fic_server
RUN mosquitto_passwd -b /etc/mosquitto/passwd fic_server fic_password

# Configurar el comando para iniciar mosquitto con la configuración deseada
CMD ["/usr/sbin/mosquitto", "-c", "/etc/mosquitto/mosquitto.conf"]