#!/bin/bash
# Complete Setup Script for webservisiiute.siglife.mk
# Run as root on AlmaLinux 9.5

# ===== 1. SYSTEM CONFIGURATION =====
echo "Setting hostname and basic configuration..."
hostnamectl set-hostname webservisiiute.siglife.mk
echo "192.168.100.61 webservisiiute.siglife.mk webservisiiute" >> /etc/hosts

# ===== 2. INSTALL DEPENDENCIES =====
echo "Installing required packages..."
dnf install -y epel-release
dnf install -y python3.11 python3.11-devel python3.11-pip git nginx certbot python3-certbot-nginx \
               gcc openssl-devel bzip2-devel libffi-devel zlib-devel firewalld

# ===== 3. CONFIGURE FIREWALL/NAT =====
echo "Configuring firewall and NAT..."
systemctl enable --now firewalld
firewall-cmd --permanent --add-service=http --add-service=https
firewall-cmd --permanent --add-port=8000/tcp
firewall-cmd --reload

# NAT Configuration (run on router/firewall)
echo "Add these NAT rules to your router/firewall:"
echo "iptables -t nat -A PREROUTING -d 62.162.114.84 -j DNAT --to-destination 192.168.100.61"
echo "iptables -A FORWARD -d 192.168.100.61 -j ACCEPT"

# ===== 4. DEPLOY SOAP SERVICE =====
echo "Deploying SOAP service..."
mkdir -p /opt/soap_service
git clone https://github.com/supportuniqa/soap-web-services.git /opt/soap_service
cd /opt/soap_service

python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install spyne lxml pyopenssl cryptography

# Create production .env
cat > /opt/soap_service/server/.env <<EOF
SECRET_KEY=$(openssl rand -hex 32)
SERVICE_USER=prod_admin
SERVICE_PASSWORD=$(tr -dc A-Za-z0-9_\!\@\#\$\%\^\&* < /dev/urandom | head -c 24)
SYSTEM_MODE=LIVE
MAX_REQUEST_SIZE_MB=25
SSL_CERT_PATH=
SSL_KEY_PATH=
LOG_LEVEL=INFO
LOG_FILE_PATH=/var/log/soap_service/server.log
SERVER_HOST=127.0.0.1
SOAP_SERVER_PORT=8000
CLIENT_SSL_VERIFY=True
EOF

# ===== 5. SYSTEMD SERVICE =====
echo "Creating systemd service..."
cat > /etc/systemd/system/soap_service.service <<EOF
[Unit]
Description=SOAP Web Service
After=network.target

[Service]
User=root
WorkingDirectory=/opt/soap_service/server
EnvironmentFile=/opt/soap_service/server/.env
ExecStart=/opt/soap_service/venv/bin/python /opt/soap_service/server/app.py
Restart=always
RestartSec=5s
LimitNOFILE=65535
LimitNPROC=65535

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now soap_service

# ===== 6. NGINX + SSL CONFIGURATION =====
echo "Configuring Nginx reverse proxy..."

# Get Let's Encrypt certificate (will prompt for email)
certbot certonly --standalone -d webservisiiute.siglife.mk --agree-tos --non-interactive

# Create Nginx config
cat > /etc/nginx/conf.d/soap.conf <<EOF
upstream soap_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name webservisiiute.siglife.mk;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name webservisiiute.siglife.mk;

    ssl_certificate /etc/letsencrypt/live/webservisiiute.siglife.mk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/webservisiiute.siglife.mk/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    location / {
        client_max_body_size 25m;
        proxy_pass http://soap_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    add_header Strict-Transport-Security "max-age=63072000" always;
}
EOF

# Test and restart Nginx
nginx -t && systemctl restart nginx

# ===== 7. LOG ROTATION =====
echo "Setting up log rotation..."
mkdir -p /var/log/soap_service
touch /var/log/soap_service/server.log
chown -R root:root /var/log/soap_service

cat > /etc/logrotate.d/soap_service <<EOF
/var/log/soap_service/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 640 root root
}
EOF

# ===== 8. FINAL CHECKS =====
echo "Verifying services..."
systemctl status soap_service nginx firewalld

echo "Testing endpoints..."
curl -vk --resolve webservisiiute.siglife.mk:443:127.0.0.1 https://webservisiiute.siglife.mk

echo "=== SETUP COMPLETE ==="
echo "1. Configure DNS A record: webservisiiute.siglife.mk → 62.162.114.84"
echo "2. Add NAT rules to your router if not already done"
echo "3. Access your service at: https://webservisiiute.siglife.mk"
