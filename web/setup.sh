#!/usr/bin/env bash
# Oil Wells Map – Setup Script
# Usage:  chmod +x setup.sh  &&  sudo ./setup.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=============== Oil Wells Map - Setup ==============="

# 1. Install Apache + Python deps
echo "[1] Installing packages..."
apt-get update -qq
apt-get install -y -qq apache2 python3 python3-pip > /dev/null 2>&1
a2enmod proxy proxy_http > /dev/null 2>&1
pip3 install --break-system-packages -q flask mysql-connector-python
echo "[1] Done.