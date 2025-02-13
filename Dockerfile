# Builder Stage: copy code, create virtualenv, build wheel and install
FROM cgr.dev/chainguard/wolfi-base AS builder
ARG PYVERSION=3.12
ARG GUNICORN==23.0.0
ARG PSYCOPG2==2.9.9

# Basic environment variables
ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/privacyidea/venv/bin:$PATH"

# Install Python, pip, build tools 
RUN apk add --no-cache python-${PYVERSION} py${PYVERSION}-pip build-base

WORKDIR /privacyidea
# Copy the entire source code (incl. submodules - ensure beforehand via git checkout and git submodule update)
COPY . .

# Set ownership and switch to a non-root user
RUN chown -R nonroot:nonroot /privacyidea
USER nonroot

# Create a virtualenv, upgrade pip and install the build tool
RUN python3 -m venv venv && \
    venv/bin/pip install --upgrade pip build

# Build the privacyIDEA package as a wheel and install it and other runtime dependencies
RUN venv/bin/python -m build --wheel --outdir dist && \
    venv/bin/pip install --find-links=dist dist/*.whl && \
    venv/bin/pip install psycopg2-binary==${PSYCOPG2} gunicorn==${GUNICORN}

# Copy configuration files and scripts
COPY deploy/docker/entrypoint.sh entrypoint.sh
COPY deploy/docker/healthcheck.py healthcheck.py
COPY deploy/docker/pi.cfg etc/pi.cfg
COPY deploy/docker/logging.cfg etc/logging.cfg

# Final Stage: Lean runtime image - only transfer required files
FROM cgr.dev/chainguard/wolfi-base
ARG PYVERSION=3.12

ENV PYTHONUNBUFFERED=1 \
    PATH="/privacyidea/venv/bin:/privacyidea/bin:$PATH" \
    PRIVACYIDEA_CONFIGFILE="/privacyidea/etc/pi.cfg" \
    PYTHONPATH=/privacyidea

WORKDIR /privacyidea
VOLUME /privacyidea/etc/persistent

# Install the Python interpreter (without build tools)
RUN apk add --no-cache python-${PYVERSION}

# Take over only the virtualenv and the etc folder and scripts from the builder stage
COPY --from=builder /privacyidea/venv venv
COPY --from=builder /privacyidea/etc etc
COPY --from=builder /privacyidea/healthcheck.py healthcheck.py
COPY --from=builder /privacyidea/entrypoint.sh entrypoint.sh

# Expand the port (the environment variable PORT should be set)
EXPOSE ${PORT}

# Start the privacyIDEA server via the EntryPoint script
ENTRYPOINT ["./entrypoint.sh"]

# Start Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD python /privacyidea/healthcheck.py
