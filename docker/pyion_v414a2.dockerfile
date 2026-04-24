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
# Install ion_server HTTP bridge dependencies
# =====================================================
RUN pip3 install fastapi uvicorn

# Make PID1 sane inside Docker (signal forwarding/reaping)
ENTRYPOINT ["/usr/bin/tini","--"]

CMD ["tail", "-f", "/dev/null"]
