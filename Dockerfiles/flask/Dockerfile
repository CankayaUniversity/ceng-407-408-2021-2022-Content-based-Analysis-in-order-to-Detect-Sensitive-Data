FROM debian:latest
WORKDIR /usr/src/app
RUN apt-get update && apt-get -y --no-install-recommends install python3 python3-pip
RUN rm -rf src
RUN mkdir src
COPY src/ src/
WORKDIR /usr/src/app/src/
RUN pip3 install flask
EXPOSE 5000
CMD [ "python3", "./app.py" ]
