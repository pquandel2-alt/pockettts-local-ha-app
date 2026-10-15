#!/bin/bash
# Erzeugt das Installationspaket der App (OHNE Modellgewichte). Ausgabe: ./dist oder erstes Argument.
set -euo pipefail; cd "$(dirname "$0")/.."; D=${1:-./dist}; mkdir -p $D
tar --exclude='__pycache__' --owner=0 --group=0 --numeric-owner --sort=name -czf $D/pockettts_local_int8-app.tar.gz pockettts_local_int8 repository.yaml README.md
( cd $D && sha256sum pockettts_local_int8-app.tar.gz > pockettts_local_int8-app.tar.gz.sha256 && ls -la )
