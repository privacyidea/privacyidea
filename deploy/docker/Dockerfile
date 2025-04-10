ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim AS builder

ARG GUNICORN=23.0.0
# TODO: we should probably create a different container image for use with postgres
ARG PSYCOPG2=2.9.10

# Set environment variables to optimize Python for docker
ENV PYTHONDONTWRITEBYTECODE=1

RUN python3 -m venv /opt/privacyidea

WORKDIR /build

ENV PATH="/opt/privacyidea/bin:$PATH"

RUN /opt/privacyidea/bin/pip install --no-cache-dir --upgrade pip setuptools

RUN /opt/privacyidea/bin/pip install --no-cache-dir psycopg2-binary==${PSYCOPG2} gunicorn==${GUNICORN}

COPY requirements.txt .

RUN /opt/privacyidea/bin/pip install --no-cache-dir -r requirements.txt

COPY README.rst MANIFEST.in setup.py ./
COPY ./deploy/ ./deploy
COPY ./migrations/ ./migrations
COPY ./tools/ ./tools
COPY ./privacyidea/ ./privacyidea

RUN /opt/privacyidea/bin/pip install --no-cache-dir .

# Final Stage: Create a slim image only with necessary files
FROM python:${PYTHON_VERSION}-slim

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=999
ARG GID=999
RUN groupadd --system --gid "${GID}" privacyidea && \
    useradd --no-log-init --no-create-home --shell /usr/sbin/nologin \
            --system --gid "${GID}" --uid "${UID}" privacyidea

# Set environment variables to optimize Python
# PYTHONUNBUFFERED Keeps Python from buffering stdout and stderr to avoid situations
# where the application crashes without emitting any logs due to buffering.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy the privacyIDEA virtuelenv from the builde
COPY --chown=privacyidea:privacyidea --from=builder /opt/privacyidea/ /opt/privacyidea/
COPY --chown=privacyidea:privacyidea --chmod=755 deploy/docker/entrypoint.sh /opt/privacyidea/

WORKDIR /opt/privacyidea

# Add a volume for the configuration
VOLUME /etc/privacyidea

ENV PATH="/opt/privacyidea/bin:$PATH" \
    PI_CONFIG_NAME="docker"

# Switch to non-root user
USER privacyidea

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]

# Disable health check for now since the container start-up and configuration is not handled yet
#HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
#  CMD /opt/privacyidea/bin/python -c "import requests; res = requests.get('http://localhost:80', timeout=3); exit(0 if res.ok else 1);"
