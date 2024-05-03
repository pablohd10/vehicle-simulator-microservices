FROM mariadb:latest

# Install mysql client
RUN apt-get update && apt-get install -y mysql-client

ADD initial_script.sql /docker-entrypoint-initdb.d/ddl.sql
