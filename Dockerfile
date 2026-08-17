FROM python:3.12

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    gcc \
    python3-dev \
    g++ \
    swig \
    cmake \
    cron && \
    apt-get clean && \
    rm -rf /var/cache/apt/* && \
    rm -rf /var/lib/apt/lists/*

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

COPY pyproject.toml /app/
COPY libs /app/libs

RUN pdm add -G build scikit-build setuptools wheel pdm-backend hatchling --no-isolation --no-sync -v && pdm install --no-isolation -v

COPY . .
RUN chmod -R +x /app/_template_core/docker/scripts

RUN echo 'source $(pdm venv list | grep -o "/venv/[^ ]*")/bin/activate' >> /etc/bash.bashrc
RUN echo 'export PS1="\[\033[1;32m\][DOCKER - BASH MODE]\[\033[0m\] \\u@\\h:\\w\\$ "' >> /etc/bash.bashrc


ENTRYPOINT ["/app/_template_core/docker/scripts/entrypoint.sh"]