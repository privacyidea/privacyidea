FROM cgr.dev/chainguard/wolfi-base AS builder

ARG PYTHON_VERSION=3.13
ARG NODEJS_VERSION=22

ARG GUNICORN=23.0.0
# TODO: we should probably create a different container image for use with postgres
ARG PSYCOPG2=2.9.10

# TODO: Add build steps for gssapi and PyKCS11

# Set environment variables to optimize Python for docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python, pip, build tools
RUN apk add --no-cache python-${PYTHON_VERSION} py${PYTHON_VERSION}-pip build-base git nodejs-${NODEJS_VERSION} npm

RUN python3 -m venv /opt/privacyidea

WORKDIR /build

ENV PATH="/opt/privacyidea/bin:$PATH"

RUN /opt/privacyidea/bin/pip install --no-cache-dir --upgrade pip setuptools

RUN /opt/privacyidea/bin/pip install --no-cache-dir psycopg2-binary==${PSYCOPG2} gunicorn==${GUNICORN}

COPY requirements.txt .

RUN /opt/privacyidea/bin/pip install --no-cache-dir -r requirements.txt

COPY README.rst MANIFEST.in pyproject.toml ./
COPY ./.git ./.git
COPY ./deploy/ ./deploy
COPY ./tools/ ./tools
COPY ./privacyidea/ ./privacyidea

# Build the new WebUI
# TODO: This could be done in a separate builder image
WORKDIR /build/privacyidea/static_new
RUN npm ci
RUN npm run-script ng build
RUN rm -rf node_modules

WORKDIR /build

RUN /opt/privacyidea/bin/pip install --no-cache-dir .

# Final Stage: Create a slim image only with necessary files
FROM cgr.dev/chainguard/wolfi-base

ARG PYTHON_VERSION=3.13
RUN apk add --no-cache python-${PYTHON_VERSION}

WORKDIR /opt/privacyidea

# Add path to volume for the configuration and set rights for user.
# See https://serverfault.com/a/984599
RUN mkdir /etc/privacyidea && \
    chown -R nonroot:nonroot /etc/privacyidea

# Switch to non-root user
USER nonroot

VOLUME /etc/privacyidea

EXPOSE 8080

# Set environment variables to optimize Python
# PYTHONUNBUFFERED Keeps Python from buffering stdout and stderr to avoid situations
# where the application crashes without emitting any logs due to buffering.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/privacyidea/bin:$PATH" \
    PI_CONFIG_NAME="docker"

# Copy the privacyIDEA virtuelenv from the builde
COPY --chown=nonroot:nonroot --from=builder /opt/privacyidea/ /opt/privacyidea/
COPY --chown=nonroot:nonroot --chmod=755 deploy/docker/entrypoint.sh /opt/privacyidea/

ENTRYPOINT ["./entrypoint.sh"]

# Disable health check for now since the container start-up and configuration is not handled yet
#HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
#  CMD /opt/privacyidea/bin/python -c "import requests; res = requests.get('http://localhost:80', timeout=3); exit(0 if res.ok else 1);"
