#!/usr/bin/env bash

set -e

# Python
poetry completions bash >> ~/.bash_completion
poetry install
poetry run pre-commit install

# Ruby
export GEM_HOME=$HOME/.gem
cd html && bundle install