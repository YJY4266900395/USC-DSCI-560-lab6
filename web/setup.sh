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
pip3 install --break-system-packages --ignore-installed -q flask mysql-connector-python
echo "[1] Done."

# 2. Setup MySQL user & database 
echo "[2] Setting up MySQL user & database..."
mysql -u root << 'EOSQL'
CREATE DATABASE IF NOT EXISTS dsci560_lab6;
CREATE USER IF NOT EXISTS 'labuser'@'localhost' IDENTIFIED BY 'labpass';
GRANT ALL PRIVILEGES ON dsci560_lab6.* TO 'labuser'@'localhost';
FLUSH PRIVILEGES;
EOSQL
echo "[2] Done. (database: dsci560_lab6, user: labuser)"

# 3. Write Apache config
echo "[3] Configuring Apache..."
cat > /etc/apache2/sites-available/oilwells.conf << 'EOF'
<VirtualHost *:80>
    ServerName localhost
    ProxyPreserveHost On
    ProxyPass        /  http://127.0.0.1:5000/
    ProxyPassReverse /  http://127.0.0.1:5000/
</VirtualHost>
EOF
a2dissite 000-default > /dev/null 2>&1 || true
a2ensite oilwells > /dev/null 2>&1
echo "[3] Done."

# 3. Start Flask
echo "[4] Starting Flask..."
pkill -f "python3.*app.py" 2>/dev/null || true
sleep 1
cd "$DIR"
nohup python3 app.py > flask.log 2>&1 &
echo "[4] Flask PID: $! (log: flask.log)"

# ── 4. Restart Apache ────────────────────────────────────
echo "[5] Restarting Apache..."
systemctl restart apache2
echo "[5] Done."

echo ""
echo " =============== READY! http://localhost ==============="