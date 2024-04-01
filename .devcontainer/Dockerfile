# See here for image contents: https://github.com/devcontainers/images/blob/c0887a58a0d7dca45f86ba8da94cafc222b52b58/src/python/.devcontainer/Dockerfile

ARG VARIANT="1-3.12-bullseye"
FROM mcr.microsoft.com/vscode/devcontainers/python:${VARIANT}

USER vscode

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

# Update Debian
RUN \
  sudo apt-get -y update

# Install Python and dependecies
RUN \
  pipx install poetry pre-commit \
  && poetry completions bash >> ~/.bash_completion

# Install rbenv, Ruby and bundler
RUN \
  sudo apt-get install -y rbenv rubygems \
  && git clone https://github.com/rbenv/ruby-build.git --depth 1 \
    "$(rbenv root)"/plugins/ruby-build \
  && echo 'eval "$(rbenv init -)"' >> ~/.bashrc

RUN \
  rbenv install 3.3.0 \
  && rbenv global 3.3.0