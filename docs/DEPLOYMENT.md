# Deployment Guide: Nergal Bot on Ubuntu 22.04 VPS

This guide provides step-by-step instructions for deploying the Nergal Telegram bot on a fresh Ubuntu 22.04 VPS with security best practices.

## Table of Contents

1. [Initial Server Setup & Security Hardening](#1-initial-server-setup--security-hardening)
2. [Install Docker](#2-install-docker)
3. [Clone Repository](#3-clone-repository)
4. [Configure Environment](#4-configure-environment)
5. [Deploy with Docker Compose](#5-deploy-with-docker-compose)
6. [Management Commands](#6-management-commands)
7. [Optional: Reverse Proxy with SSL](#7-optional-reverse-proxy-with-ssl)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Initial Server Setup & Security Hardening

> ⚠️ **Важно**: Все действия изначально выполняются от root, но мы сразу создадим обычного пользователя и переключимся на него.

### 1.1 Connect to your VPS

```bash
ssh root@your_vps_ip
```

### 1.2 Update the system

```bash
apt update && apt upgrade -y
```

### 1.3 Create a non-root user

```bash
# Create user with home directory
adduser deployer

# Add to sudo group
usermod -aG sudo deployer
```

### 1.4 Set up SSH key authentication (КРИТИЧНО для безопасности)

**На вашей локальной машине** (не на VPS):

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy public key to VPS
ssh-copy-id deployer@your_vps_ip
```

**Или вручную на VPS** (от root):

```bash
# Switch to deployer user
su - deployer

# Create .ssh directory
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key
nano ~/.ssh/authorized_keys
# Вставьте содержимое вашего публичного ключа (обычно ~/.ssh/id_ed25519.pub)

# Set correct permissions
chmod 600 ~/.ssh/authorized_keys

# Return to root
exit
```

### 1.5 Harden SSH configuration

```bash
# Backup original config
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Edit SSH config
nano /etc/ssh/sshd_config
```

Измените следующие параметры:

```ssh
# Disable root login
PermitRootLogin no

# Disable password authentication (only SSH keys)
PasswordAuthentication no
PubkeyAuthentication yes

# Change default port (optional but recommended)
Port 2222

# Limit authentication attempts
MaxAuthTries 3

# Disconnect idle sessions after 5 minutes
ClientAliveInterval 300
ClientAliveCountMax 2

# Allow only specific users (optional)
AllowUsers deployer
```

Примените изменения:

```bash
# Test configuration before restarting
sshd -t

# If no errors, restart SSH
systemctl restart sshd
```

> ⚠️ **Важно**: Не закрывайте текущую SSH сессию! Откройте новое окно терминала и попробуйте подключиться с новыми настройками перед тем, как закрыть текущую сессию.

### 1.6 Set up firewall

```bash
# Allow SSH (use your custom port if you changed it)
sudo ufw allow OpenSSH
# If you changed SSH port:
# sudo ufw allow 2222/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### 1.7 Install fail2ban (защита от брутфорса)

```bash
apt install fail2ban -y

# Create local configuration
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
# If you changed SSH port:
# port = 2222
EOF

# Enable and start
systemctl enable fail2ban
systemctl start fail2ban

# Check status
fail2ban-client status sshd
```

### 1.8 Switch to non-root user

Теперь переключитесь на обычного пользователя для всех дальнейших действий:

```bash
# Exit from root
exit

# Connect as deployer (from your local machine)
ssh -p 2222 deployer@your_vps_ip
```

Все последующие команды выполняются от пользователя `deployer` с использованием `sudo` где необходимо.

---

## 2. Install Docker

### 2.1 Install Docker using the convenience script

```bash
# Download and run the Docker installation script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### 2.2 Add user to docker group

```bash
# Add current user to docker group
sudo usermod -aG docker $USER

# Apply changes (log out and log back in, or run)
newgrp docker
```

### 2.3 Verify Docker installation

```bash
docker --version
docker compose version
```

### 2.4 Enable Docker to start on boot

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 3. Clone Repository

### 3.1 Install Git

```bash
sudo apt install git -y
```

### 3.2 Clone the repository

```bash
# Create apps directory
mkdir -p ~/apps
cd ~/apps

# Clone the repository
git clone https://github.com/finnetrolle/nergal.git
cd nergal
```

---

## 4. Configure Environment

### 4.1 Create .env file

```bash
# Copy example file
cp .env.example .env
```

### 4.2 Edit configuration

```bash
nano .env
```

### 4.3 Required configuration

Update the following values in `.env`:

```env
# Telegram Bot Token (required)
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here

# LLM Configuration (required)
LLM_PROVIDER=zai
LLM_API_KEY=your_actual_api_key_here
LLM_MODEL=glm-4-flash

# Optional: Enable web search
WEB_SEARCH_ENABLED=true
WEB_SEARCH_MCP_URL=https://api.z.ai/api/mcp/web_search_prime/mcp
```

Save with `Ctrl+O`, exit with `Ctrl+X`.

---

## 5. Deploy with Docker Compose

### 5.1 Build and start the bot

```bash
cd ~/apps/nergal

# Build and run in detached mode
docker compose up -d --build
```

### 5.2 Check container status

```bash
docker compose ps
```

### 5.3 View logs

```bash
# View all logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# View last 100 lines
docker compose logs --tail 100
```

---

## 6. Management Commands

### 6.1 Start the bot

```bash
cd ~/apps/nergal
docker compose start
```

### 6.2 Stop the bot

```bash
cd ~/apps/nergal
docker compose stop
```

### 6.3 Restart the bot

```bash
cd ~/apps/nergal
docker compose restart
```

### 6.4 Update the bot

```bash
cd ~/apps/nergal

# Pull latest changes
git pull

# Rebuild and restart
docker compose up -d --build
```

### 6.5 View resource usage

```bash
docker stats nergal-bot
```

### 6.6 Remove old Docker images (cleanup)

```bash
docker system prune -f
```

---

## 7. Optional: Reverse Proxy with SSL

If you need to expose any HTTP endpoints (not required for basic Telegram bot):

### 7.1 Install Nginx

```bash
sudo apt install nginx -y
```

### 7.2 Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 7.3 Configure Nginx

Create a configuration file:

```bash
sudo nano /etc/nginx/sites-available/nergal
```

Example configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/nergal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7.4 Get SSL certificate

```bash
sudo certbot --nginx -d your-domain.com
```

---

## 8. Troubleshooting

### 8.1 Container won't start

```bash
# Check logs for errors
docker compose logs

# Check if .env file exists and has correct values
cat .env

# Verify Docker is running
sudo systemctl status docker
```

### 8.2 Bot not responding

```bash
# Check if container is running
docker compose ps

# Check logs for Telegram API errors
docker compose logs | grep -i error

# Verify bot token is correct
# Test with Telegram API:
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

### 8.3 Permission issues

```bash
# Fix ownership
sudo chown -R $USER:$USER ~/apps/nergal

# Ensure user is in docker group
groups $USER
```

### 8.4 Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a -f

# Check log sizes
du -sh /var/lib/docker/containers/*/*-json.log
```

### 8.5 Memory issues

```bash
# Check memory usage
free -h

# Check container memory
docker stats --no-stream
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start bot | `docker compose up -d` |
| Stop bot | `docker compose stop` |
| Restart bot | `docker compose restart` |
| View logs | `docker compose logs -f` |
| Update bot | `git pull && docker compose up -d --build` |
| Check status | `docker compose ps` |

---

## Security Recommendations

### Выполненные в этом гайде:

1. ✅ **Non-root user**: Создан пользователь `deployer` с sudo доступом
2. ✅ **SSH keys**: Настроена аутентификация только по ключам
3. ✅ **Disabled root login**: Прямой вход под root запрещен
4. ✅ **Firewall (UFW)**: Настроен файрвол
5. ✅ **Fail2ban**: Защита от брутфорса атак

### Дополнительные рекомендации:

6. **Автоматические обновления безопасности**:
   ```bash
   sudo apt install unattended-upgrades -y
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

7. **Secure .env file**: Никогда не коммитьте `.env` в git
   ```bash
   # Установите правильные права
   chmod 600 ~/apps/nergal/.env
   ```

8. **Регулярные бэкапы**:
   ```bash
   # Бэкап конфигурации
   cp ~/apps/nergal/.env ~/backups/.env.$(date +%Y%m%d)
   ```

9. **Мониторинг логов**:
   ```bash
   # Проверка попыток входа
   sudo tail -f /var/log/auth.log
   
   # Проверка забаненных IP
   sudo fail2ban-client status sshd
   ```

10. **Ограничение sudo** (опционально):
    ```bash
    # Разрешить только определенные команды
    sudo visudo
    # Добавьте строку:
    # deployer ALL=(ALL) /usr/bin/docker, /usr/bin/git, /usr/bin/systemctl
    ```

### Проверка безопасности:

```bash
# Проверить открытые порты
sudo ss -tlnp

# Проверить статус файрвола
sudo ufw status verbose

# Проверить активные соединения
sudo ss -tunap

# Проверить последние входы
last -n 10

# Проверить неудачные попытки входа
sudo grep "Failed password" /var/log/auth.log | tail -10
```

---

## System Requirements

- **OS**: Ubuntu 22.04 LTS
- **RAM**: Minimum 512MB, Recommended 1GB+
- **Disk**: Minimum 5GB free space
- **CPU**: 1 vCPU minimum
