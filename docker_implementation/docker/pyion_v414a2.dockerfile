# chat_pyion_v414a2.dockerfile
ARG IMAGE_NAME=ubuntu:22.04
FROM ${IMAGE_NAME}

ENV DEBIAN_FRONTEND=noninteractive

# Set environment variables.
ENV HOME=/home
ENV ION_HOME=/home/ion-open-source-4.1.4-a.2
ENV PYION_HOME=/home/pyion-4.1.4-a.2
ENV PYION_BP_VERSION=BPv7
ENV IONDIR=/home/ion-open-source-4.1.4-a.2

# Ensure installed ION binaries are found
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /home

# =====================================================
# Install dependencies
# =====================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    man-db \
    build-essential \
    dos2unix \
    autotools-dev \
    automake \
    libtool \
    pkg-config \
    python3 \
    python3-dev \
    python3-setuptools \
    python3-pip \
    procps \
    iproute2 \
    net-tools \
    ca-certificates \
    tini \
 && rm -rf /var/lib/apt/lists/*

# =====================================================
# Download, compile and install ION
# =====================================================
RUN git clone --single-branch --branch ion-open-source-4.1.4-a.2 \
    https://github.com/nasa-jpl/ION-DTN.git "${ION_HOME}"

RUN cd "${ION_HOME}" && \
    autoreconf -fi && \
    ./configure && \
    make -j"$(nproc)" && \
    make install && \
    ldconfig

# (Optional sanity check: fail early if headers/libs aren’t where pyion expects)
RUN test -f /usr/local/include/ion.h || test -f /usr/local/include/ion/ion.h

# =====================================================
# Download and install pyion
# =====================================================
RUN git clone --single-branch --branch v4.1.4-a.2 \
    https://github.com/nasa-jpl/pyion.git "${PYION_HOME}"

RUN cd "${PYION_HOME}" && \
    find "${PYION_HOME}" -type f -print0 | xargs -0 dos2unix && \
    python3 setup.py install && \
    chmod -R +x "${PYION_HOME}"

# Now that pyion is installed, it’s safe to set LD_LIBRARY_PATH for runtime.
ENV LD_LIBRARY_PATH="/usr/local/lib"

# =====================================================
# SpaceZilla backend agent + ZMQ IPC
# =====================================================
# pyzmq is the REQ/REP + PUB transport between the host process and the
# in-container agent. Bake the backend code into the image so the agent
# can be launched via ``python3 -m backend.container_agent`` from the
# ``docker run`` CMD (no dev bind mount required in production).
RUN pip3 install --no-cache-dir pyzmq platformdirs

COPY backend /opt/spacezilla/backend
COPY runtime_logger /opt/spacezilla/runtime_logger
COPY store /opt/spacezilla/store
ENV PYTHONPATH=/opt/spacezilla

# Default REQ/REP + PUB ports inside the container. The host publishes
# ephemeral mappings via ``docker run -p 127.0.0.1:0:5555 -p 127.0.0.1:0:5556``
# and resolves them with ``docker port`` after start.
EXPOSE 5555 5556

# Make PID1 sane inside Docker (signal forwarding/reaping)
ENTRYPOINT ["/usr/bin/tini","--"]

# Default CMD stays a no-op so images can be shelled into for debugging.
# The real command is supplied by :func:`backend.docker_backend.start_container`.
CMD ["tail", "-f", "/dev/null"]
