FROM python:3.13-bookworm

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
ENV PYTHONPATH="/app/src"
ENV PATH="${JAVA_HOME}/bin:${PATH}"

RUN pip install pdm

WORKDIR /app

RUN pdm config venv.in_project false
RUN pdm config venv.location /venv
RUN pdm venv create 3.13
RUN pdm use -f $(pdm venv list | grep -o '/venv/[^ ]*')/bin/python

COPY pyproject.toml pdm.lock /app/

RUN pdm install --no-editable

COPY src ./src

COPY . .

ENTRYPOINT ["pdm", "run", "python", "-m", "ingestion_engine"]