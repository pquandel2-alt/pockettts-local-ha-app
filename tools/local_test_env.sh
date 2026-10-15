#!/bin/bash
# Lokale Testumgebung wie ein Supervisor: eigenes Netz mit "supervisor"-Mock, getrennte /data /config /share.
# Nutzung: local_test_env.sh up|down|reset   Variablen: IMAGE, HOST_PORT (Standard 10312), OPTS_JSON
set -euo pipefail
T=$(cd "$(dirname "$0")" && pwd); R=${RUN_DIR:-$T/../.run}; IMAGE=${IMAGE:-local/pockettts-local-int8:1.0.0}; HOST_PORT=${HOST_PORT:-10312}; NAME=${NAME:-pockettts-app-test}
case ${1:-up} in
 reset) sudo docker rm -f $NAME pt-mock-supervisor >/dev/null 2>&1 || true; sudo rm -rf $R; mkdir -p $R/data $R/config $R/share $R/out; sudo docker network rm hatest >/dev/null 2>&1 || true ;;
 down)  sudo docker rm -f $NAME pt-mock-supervisor >/dev/null 2>&1 || true; sudo docker network rm hatest >/dev/null 2>&1 || true ;;
 up)
  mkdir -p $R/data $R/config $R/share $R/out
  echo "${OPTS_JSON:-{\}}" | sudo tee $R/data/options.json >/dev/null
  sudo docker network inspect hatest >/dev/null 2>&1 || sudo docker network create hatest >/dev/null
  sudo docker rm -f pt-mock-supervisor $NAME >/dev/null 2>&1 || true
  sudo docker run -d --name pt-mock-supervisor --network hatest --network-alias supervisor -v $T/mock_supervisor.py:/m.py:ro -v $R/out:/out python:3.12-slim python /m.py >/dev/null
  # Parameter wie sie der Supervisor setzt: init=false (kein --init), tmpfs /tmp, Port-Mapping, Hostname, Token
  sudo docker run -d --name $NAME --network hatest --hostname testapp --tmpfs /tmp --security-opt no-new-privileges:true \
    -e SUPERVISOR_TOKEN=test-token -v $R/data:/data -v $R/config:/config -v $R/share:/share:ro -p $HOST_PORT:10302 ${EXTRA_DOCKER_ARGS:-} $IMAGE >/dev/null
  echo "gestartet: $NAME (Wyoming auf Host-Port $HOST_PORT)";;
esac
