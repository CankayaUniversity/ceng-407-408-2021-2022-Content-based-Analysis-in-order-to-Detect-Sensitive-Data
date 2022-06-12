FROM debian:latest
WORKDIR /usr/src/app
RUN apt-get update && apt-get -y --no-install-recommends install poppler-utils python3 python3-pip libtesseract-dev
RUN rm -rf src
RUN mkdir src
COPY src/ src/
WORKDIR /usr/src/app/src/
RUN pip install -r requirements.txt
EXPOSE 1235
CMD [ "python3", "./main.py" ]
