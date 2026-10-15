#!/bin/sh
# Alle Tests im App-Container: docker run --rm --entrypoint /opt/app/tests/run_tests.sh <image>
cd /opt/app && exec /opt/venv/bin/python -m unittest discover -s tests -t . -v
