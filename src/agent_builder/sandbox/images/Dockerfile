# Agent Team Builder — Layer 2 sandbox base image (F4.4)
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pyinstaller>=6.0.0 \
    ruff>=0.6.0 \
    mypy>=1.10.0 \
    pytest>=8.0.0

RUN useradd -m -u 1000 -s /bin/bash sandbox

USER sandbox
WORKDIR /workspace
