# SPDX-FileCopyrightText: (C) 2025 NetKnights GmbH <https://netknights.it>
#
# SPDX-License-Identifier: CC0-1.0

# ── Stage 1: Build the Angular frontend ──────────────────────────────────────
FROM cgr.dev/chainguard/wolfi-base AS node-builder

ARG NODEJS_VERSION=22

RUN apk add --no-cache nodejs-${NODEJS_VERSION} npm

WORKDIR /build/privacyidea/static_new

# Install dependencies first (better layer caching — only re-runs when
# package.json / package-lock.json change, not on every source change).
COPY privacyidea/static_new/package.json privacyidea/static_new/package-lock.json ./
RUN npm ci

COPY privacyidea/static_new/ ./
RUN npm run build

# ── Stage 2: Build the Python virtualenv ─────────────────────────────────────
FROM cgr.dev/chainguard/wolfi-base AS python-builder

ARG PYTHON_VERSION=3.13
ARG GUNICORN=23.0.0
ARG PSYCOPG2=2.9.10

# To override the package version since we copy only part of the repository.
# See https://setuptools-scm.readthedocs.io/en/latest/usage/#with-dockerpodman
ARG GIT_VERSION

# Set environment variables to optimize Python for docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Split into two RUN commands so a transient network timeout on one package
# group does not force a full re-download of everything.
RUN apk add --no-cache python-${PYTHON_VERSION} py${PYTHON_VERSION}-pip
RUN apk add --no-cache build-base git

RUN python3 -m venv /opt/privacyidea

WORKDIR /build

ENV PATH="/opt/privacyidea/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools

RUN pip install --no-cache-dir psycopg2-binary==${PSYCOPG2} gunicorn==${GUNICORN}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY README.rst MANIFEST.in pyproject.toml ./
COPY ./.git ./.git
COPY ./deploy/ ./deploy
COPY ./tools/ ./tools
COPY ./privacyidea/ ./privacyidea

# Copy the pre-built Angular frontend from the node-builder stage
COPY --from=node-builder /build/privacyidea/static_new/dist/ ./privacyidea/static_new/dist/

RUN SETUPTOOLS_SCM_PRETEND_VERSION_FOR_PRIVACYIDEA=${GIT_VERSION} pip install --no-cache-dir .

# ── Stage 3: Final slim runtime image ────────────────────────────────────────
FROM cgr.dev/chainguard/wolfi-base

ARG PYTHON_VERSION=3.13
RUN apk add --no-cache python-${PYTHON_VERSION}

WORKDIR /opt/privacyidea

RUN mkdir /etc/privacyidea && \
    chown -R nonroot:nonroot /etc/privacyidea

USER nonroot

COPY --chown=nonroot:nonroot ./deploy/privacyidea/NetKnights.pem /etc/privacyidea/
COPY --chown=nonroot:nonroot ./deploy/privacyidea/dictionary* /etc/privacyidea/

VOLUME /etc/privacyidea

EXPOSE 8080

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/privacyidea/bin:$PATH" \
    PI_CONFIG_NAME="docker"

COPY --chown=nonroot:nonroot --from=python-builder /opt/privacyidea/ /opt/privacyidea/
COPY --chown=nonroot:nonroot --chmod=755 deploy/docker/entrypoint.sh /opt/privacyidea/

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python3 -c "import urllib.request, os; urllib.request.urlopen('http://localhost:' + os.environ.get('PI_PORT', '8080') + '/healthz/livez')" || exit 1

ENTRYPOINT ["./entrypoint.sh"]

