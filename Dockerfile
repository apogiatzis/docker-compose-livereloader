FROM python:3.7

RUN apt-get -y update \
    && apt -y install docker.io \
    && curl -L "https://github.com/docker/compose/releases/download/1.25.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY ./src /reloader

WORKDIR /reloader

ENTRYPOINT python -u main.py
