#!/usr/bin/env bash

# pdm export -p . -o requirements.txt --without-hashes

uv export --no-hashes --output-file requirements.txt
