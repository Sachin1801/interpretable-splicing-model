#!/bin/bash
# Run this on the Ubuntu 24.04 VM to prepare for deployment

set -e

echo "=== Installing Docker ==="
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

echo "=== Installing Docker Compose ==="
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

echo "=== Installing Apache ==="
sudo apt-get install -y apache2
sudo a2enmod proxy proxy_http proxy_wstunnel rewrite headers

echo "=== Creating application directory ==="
sudo mkdir -p /opt/splicing-model
sudo chown $USER:$USER /opt/splicing-model

echo "=== Creating Docker volume for database ==="
docker volume create splicing-db

echo "=== Setup complete ==="
echo "Next steps:"
echo "1. Copy docker-compose.prod.yml to /opt/splicing-model/"
echo "2. Create .env.production file with secrets"
echo "3. Configure Apache site: sudo cp apache-site.conf /etc/apache2/sites-available/splicing.conf"
echo "4. Enable site: sudo a2ensite splicing && sudo systemctl reload apache2"
echo "5. Add GitHub Secrets for deployment"
