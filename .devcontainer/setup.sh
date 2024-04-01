#!/usr/bin/env bash

set -e

# Python
poetry install

# Ruby
cd html && bundle install