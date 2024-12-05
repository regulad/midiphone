# https://stackoverflow.com/questions/53835198/integrating-python-poetry-with-docker/54763270#54763270
# Copyright (c) 2023  Parker Wahle - Licensed under MIT License (do whatever you want)

FROM python:3.12.3-alpine3.18 AS base

# In Python, the line between a compile-time and run-time dependency is blurry,
# so we play it safe by installing everything
RUN apk add -U tzdata --no-cache \
    && apk add gcc musl-dev libffi-dev openssl-dev make git curl --no-cache \
    && pip install --upgrade pip

# --------------------------------------
# ---------- Copy and compile ----------
# We use a multi-stage build to reduce the size of the final image
FROM base AS builder

# Configure env variables for build/install
# ENV no longer adds a layer in new Docker versions,
# so we don't need to chain these in a single line
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=120
ENV POETRY_VERSION=1.5.1

# Install system deps
RUN pip install "poetry==$POETRY_VERSION"

# Copy only requirements to cache them in docker layer
WORKDIR /code
# Although it would be very convienient to only copy the pyproject.toml file so that we can cache the dependencies,
# Poetry requires the whole project to be present in order to install the dependencies
COPY . /code

# Install with poetry
# pip install would probably work, too, but we'd have to make sure it's a recent enough pip
# Don't bother creating a virtual env -- significant performance increase
RUN poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --only main

# Build the package
RUN poetry build

# --------------------------------------
# ---------- Install & run! ------------
FROM base AS runner

# Set labels

# See https://github.com/opencontainers/image-spec/blob/master/annotations.md
LABEL name="midiphone"
LABEL version="0.1.0"
LABEL vendor="Parker Wahle"
LABEL org.opencontainers.image.title="midiphone"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.url="https://github.com/regulad/midiphone"
LABEL org.opencontainers.image.documentation="https://midiphone.readthedocs.io"

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV TZ=America/New_York

ARG USERNAME=midiphone
ARG USER_UID=1008
ARG USER_GID=$USER_UID

RUN addgroup -g $USER_GID -S $USERNAME \
    && adduser -u $USER_UID -G $USERNAME -D -S $USERNAME

# Switch to non-root user (for security)
# This makes dockerfile_lint complain, but it's fine
# dockerfile_lint - ignore
USER $USERNAME

# Install the package in the user space
COPY --from=builder /code/dist/midiphone-*.whl /tmp/
RUN pip install --user /tmp/midiphone-*.whl

# Now do something!
CMD ["/home/midiphone/.local/bin/midiphone"]

# or expose a port:
# EXPOSE 8080/tcp
