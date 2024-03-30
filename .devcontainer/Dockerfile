# See here for image contents: https://github.com/devcontainers/images/blob/c0887a58a0d7dca45f86ba8da94cafc222b52b58/src/python/.devcontainer/Dockerfile

ARG VARIANT="1-3.12-bullseye"
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Update Debian
RUN \
  apt-get update

# Install Python and dependecies
RUN \
  pipx install poetry

# Install Ruby and dependencies
RUN \
  apt-get install -y ruby-full build-essential zlib1g-dev \
  && gem install jekyll bundler