FROM python:3.12-slim AS builder
ARG GUNICORN=23.0.0
ARG PSYCOPG2=2.9.10

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

RUN python3 -m venv /opt/privacyidea

ENV PATH="/opt/privacyidea/bin:$PATH"

RUN /opt/privacyidea/bin/pip install --no-cache-dir --upgrade pip setuptools

RUN /opt/privacyidea/bin/pip install --no-cache-dir psycopg2-binary==${PSYCOPG2} gunicorn==${GUNICORN}

COPY ./requirements.txt .

RUN /opt/privacyidea/bin/pip install --no-cache-dir -r requirements.txt

COPY ./README.rst .
COPY ./MANIFEST.in .
COPY ./setup.py .
COPY ./deploy/ ./deploy
COPY ./migrations ./migrations
COPY ./tools/ ./tools
COPY ./privacyidea/ ./privacyidea

RUN /opt/privacyidea/bin/pip install --no-cache-dir .

# Final Stage: Schlankes Runtime-Image – nur die benötigten Dateien werden übertragen
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /opt/privacyidea
VOLUME /etc/privacyidea

COPY --from=builder /opt/privacyidea/ /opt/privacyidea/

ENV PATH="/opt/privacyidea/bin:$PATH"

EXPOSE 80

ENTRYPOINT ["gunicorn", "-w", "4", "--bind", "0.0.0.0:80", "privacyidea.app:create_app(config_name='production')"]

# Disable health check for now since the container start-up and configuration is not handled yet
#HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
#  CMD /opt/privacyidea/bin/python -c "import requests; res = requests.get('http://localhost:80', timeout=3); exit(0 if res.ok else 1);"
