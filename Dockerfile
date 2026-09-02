FROM python:3.13-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    gcc \
    python3-dev \
    g++ \
    swig \
    cmake \
    openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PYTHONPATH="/app/src"
ENV PATH="${JAVA_HOME}/bin:${PATH}"

RUN pip install --no-cache-dir "pdm==2.28.1"

RUN useradd --create-home --uid 10001 ingestion \
    && mkdir -p /app /venv \
    && chown -R ingestion:ingestion /app /venv

WORKDIR /app

COPY --chown=ingestion:ingestion pyproject.toml pdm.lock ./

USER ingestion

RUN pdm config venv.in_project false \
    && pdm config venv.location /venv \
    && pdm venv create 3.13 \
    && pdm use -f $(pdm venv list | grep -o '/venv/[^ ]*')/bin/python \
    && pdm install --no-editable

COPY --chown=ingestion:ingestion src ./src
COPY --chown=ingestion:ingestion config ./config

ENTRYPOINT ["pdm", "run", "python", "-m", "ingestion_engine"]