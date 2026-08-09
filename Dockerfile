FROM mcr.microsoft.com/vscode/devcontainers/base:debian

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        # Additional library needed by some tests and accordingly by VScode Tests Discovery
        bluez \
        ffmpeg \
        libudev-dev \
        libavformat-dev \
        libavcodec-dev \
        libavdevice-dev \
        libavutil-dev \
        libswscale-dev \
        libswresample-dev \
        libavfilter-dev \
        libpcap-dev \
        libturbojpeg0 \
        libyaml-dev \
        libxml2 \
        git \
        cmake \
        autoconf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/alexxit/go2rtc:latest /usr/local/bin/go2rtc /bin/go2rtc

WORKDIR /usr/src

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

USER vscode

ENV VIRTUAL_ENV="/home/vscode/.local/ha-venv" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1
ENV UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV
RUN --mount=type=bind,source=.python-version,target=.python-version \
    uv python install \
    && uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /workspaces

ENV SHELL=/bin/bash