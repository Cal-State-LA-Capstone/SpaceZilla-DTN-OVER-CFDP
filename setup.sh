#!/usr/bin/env bash
# SpaceZilla ION setup script.
# Installs ION and pyion. Safe to rerun -- skips steps already done.
# Run from the project root: bash scripts/setup.sh
set -euo pipefail

ION_VERSION="ion-open-source-4.1.4-a.2"
PYION_VERSION="v4.1.4-a.2"
ION_HOME="${HOME}/src/ION-DTN"
PYION_HOME="${HOME}/src/pyion"
VENV_PYTHON="$(pwd)/.venv/bin/python"

export ION_HOME
export PYION_BP_VERSION=BPv7
export LD_LIBRARY_PATH=/usr/local/lib:${LD_LIBRARY_PATH:-}

# =====================================================
# System dependencies
# =====================================================
echo "--- Installing system dependencies"
sudo apt-get update -q
sudo apt-get install -y --no-install-recommends \
    git \
    build-essential \
    autotools-dev \
    automake \
    libtool \
    pkg-config \
    dos2unix \
    ca-certificates \
    python3-dev \
    python3-setuptools

# =====================================================
# ION
# =====================================================
if command -v ionadmin >/dev/null 2>&1; then
    echo "--- ION already installed, skipping build"
else
    mkdir -p "${HOME}/src"

    if [ ! -d "${ION_HOME}" ]; then
        echo "--- Cloning ION"
        git clone --single-branch --branch "${ION_VERSION}" \
            https://github.com/nasa-jpl/ION-DTN.git "${ION_HOME}"
    else
        echo "--- ION source already present"
    fi

    echo "--- Building ION (this may take a few minutes)"
    cd "${ION_HOME}"
    autoreconf -fi
    ./configure
    make -j"$(nproc)"

    echo "--- Installing ION"
    sudo make install
    sudo ldconfig
    cd - > /dev/null
fi

echo "--- Verifying ION"
if [ -f /usr/local/include/ion.h ] || [ -f /usr/local/include/ion/ion.h ]; then
    echo "    ION headers found"
else
    echo "    ERROR: ION headers not found"
    exit 1
fi

if command -v ionadmin >/dev/null 2>&1; then
    echo "    ionadmin found"
else
    echo "    ERROR: ionadmin not found"
    exit 1
fi

# =====================================================
# pyion
# =====================================================
if [ ! -f "${VENV_PYTHON}" ]; then
    echo "ERROR: .venv not found -- run 'uv sync' first, then rerun this script"
    exit 1
fi

if "${VENV_PYTHON}" -c "import pyion" 2>/dev/null; then
    echo "--- pyion already installed, skipping"
else
    mkdir -p "${HOME}/src"

    if [ ! -d "${PYION_HOME}" ]; then
        echo "--- Cloning pyion"
        git clone --single-branch --branch "${PYION_VERSION}" \
            https://github.com/nasa-jpl/pyion.git "${PYION_HOME}"
    else
        echo "--- pyion source already present"
    fi

    echo "--- Installing setuptools into venv"
    uv pip install setuptools

    echo "--- Building and installing pyion into venv"
    cd "${PYION_HOME}"
    find . -type f -print0 | xargs -0 dos2unix
    ION_HOME="${ION_HOME}" PYION_BP_VERSION=BPv7 LD_LIBRARY_PATH=/usr/local/lib "${VENV_PYTHON}" setup.py install
    cd - > /dev/null

    if "${VENV_PYTHON}" -c "import pyion" 2>/dev/null; then
        echo "    pyion installed successfully"
    else
        echo "    ERROR: pyion install failed"
        exit 1
    fi
fi

# =====================================================
# lib.env
# =====================================================
LIBENV="$(pwd)/lib.env"
if [ ! -f "${LIBENV}" ]; then
    echo "--- Writing lib.env"
    cat > "${LIBENV}" <<EOF
PYION_BP_VERSION=BPv7
LD_LIBRARY_PATH=/usr/local/lib
EOF
    echo "lib.env created"
else
    echo "--- lib.env already exists, skipping"
fi

# =====================================================
# Done
# =====================================================
echo ""
echo "--- Setup complete"
echo "    ION source:   ${ION_HOME}"
echo "    pyion source: ${PYION_HOME}"
echo ""
echo "    To run SpaceZilla:"
echo "      uv run --env-file lib.env main.py"