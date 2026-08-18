FROM python:3.12-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    gcc \
    python3-dev \
    g++ \
    swig \
    cmake \
    cron \
    openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

RUN pip install pdm

WORKDIR /app

ARG JFROG_XYLEM_PYPI_USER
ARG JFROG_XYLEM_PYPI_TOKEN
ARG NEXUS_PYPI_USER
ARG NEXUS_PYPI_TOKEN

ENV JFROG_XYLEM_PYPI_USER=${JFROG_XYLEM_PYPI_USER}
ENV JFROG_XYLEM_PYPI_TOKEN=${JFROG_XYLEM_PYPI_TOKEN}
ENV NEXUS_PYPI_USER=${NEXUS_PYPI_USER}
ENV NEXUS_PYPI_TOKEN=${NEXUS_PYPI_TOKEN}

RUN pdm config venv.in_project false
RUN pdm config venv.location /venv

RUN pdm venv create 3.12

RUN pdm use -f $(pdm venv list | grep -o '/venv/[^ ]*')/bin/python

COPY pyproject.toml pdm.lock /app/

COPY src ./src

RUN pdm install --check --no-editable

COPY . .