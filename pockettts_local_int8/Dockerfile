# PocketTTS Local INT8 - Home Assistant app (amd64). Reproducible multi-stage build:
#   stage 1 builds the native PocketTTS.cpp engine from a pinned upstream commit (+ documented patches),
#   stage 2 is a small Debian runtime with the engine, ONNX Runtime and a tiny Python Wyoming adapter.
# No model weights are baked in (access-restricted weights are imported once into /data, see DOCS.md).
ARG DEBIAN_IMAGE=debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f

# ---------------------------------------------------------------- engine build
FROM ${DEBIAN_IMAGE} AS engine
ARG POCKETTTS_CPP_REPO=https://github.com/netai369/PocketTTS.cpp-multilingual
ARG POCKETTTS_CPP_COMMIT=3ed176a2b238b7ddb62b4aea4e7469ae4bcc3489
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake git ca-certificates patch \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init -q . \
    && git remote add origin "${POCKETTTS_CPP_REPO}" \
    && git fetch -q --depth 1 origin "${POCKETTTS_CPP_COMMIT}" \
    && git checkout -q FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "${POCKETTTS_CPP_COMMIT}"
COPY patches /patches
RUN set -e; for p in /patches/*.patch; do echo "apply $p"; git apply --check "$p"; git apply "$p"; done
RUN cmake -B .build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build .build -j"$(nproc)" \
    && strip pocket-tts \
    && mkdir /out \
    && cp pocket-tts /out/ \
    && cp .build/_deps/onnxruntime-src/lib/libonnxruntime.so.1.23.2 /out/libonnxruntime.so.1 \
    && ls -la /out

# --------------------------------------------------------------------- runtime
FROM ${DEBIAN_IMAGE} AS runtime
ARG BUILD_VERSION=dev
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv libstdc++6 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /root/.cache /tmp/requirements.txt
COPY --from=engine /out/ /opt/pt/
COPY app /opt/app
COPY tests /opt/app/tests
ENV LD_LIBRARY_PATH=/opt/pt \
    PYTHONPATH=/opt/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ORT_DISABLE_TELEMETRY=1 \
    APP_VERSION=${BUILD_VERSION}
WORKDIR /opt/app

LABEL io.hass.name="PocketTTS Local INT8" \
      io.hass.description="High-performance offline German Text-to-Speech for Home Assistant using PocketTTS C++, ONNX Runtime INT8 and Wyoming streaming." \
      io.hass.type="app" \
      io.hass.arch="amd64" \
      io.hass.version="${BUILD_VERSION}"

# Describe/Info round trip with at least one voice (not just an open port)
HEALTHCHECK --start-period=120s --start-interval=3s --interval=30s --timeout=15s --retries=3 \
    CMD ["/opt/venv/bin/python", "-m", "pockettts_app.healthcheck"]

ENTRYPOINT ["/opt/venv/bin/python", "-u", "-m", "pockettts_app"]
