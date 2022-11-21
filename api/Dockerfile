FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /
RUN pip --disable-pip-version-check install --upgrade pip
RUN pip install -r /requirements.txt

RUN mkdir -p /app

WORKDIR /app