# Deployment Guide

## Overview
This guide covers deploying the Inventory Management System using Docker and Docker Compose, with optional monitoring and reverse proxy setup.

## Prerequisites
- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- PostgreSQL database (or use the included containerized version)

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd InventoryAppDev
```

### 2. Environment Configuration
Copy the environment template and configure your settings:
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=inventory_db
DB_USER=inventory_user
DB_PASSWORD=your_secure_password

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=5000
SECRET_KEY=your_very_secure_secret_key_here

# Optional: Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: Grafana Configuration
GRAFANA_PASSWORD=admin
```

### 3. Start the Application
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Check service status
docker-compose ps
```

### 4. Access the Application
- **Main Application**: http://localhost:5000
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## Production Deployment

### 1. Production Environment Variables
Create a production-specific environment file:
```bash
cp .env.example .env.production
```

Set production values:
```env
FLASK_ENV=production
SECRET_KEY=your_production_secret_key
DB_PASSWORD=very_secure_production_password
GRAFANA_PASSWORD=secure_grafana_password
```

### 2. Production Docker Compose
Use the production configuration:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 3. SSL/TLS Configuration
For production, configure SSL certificates:

#### Option A: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to nginx directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./nginx/ssl/
```

#### Option B: Self-Signed Certificate
```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./nginx/ssl/privkey.pem \
  -out ./nginx/ssl/fullchain.pem
```

### 4. Nginx Configuration
Update the Nginx configuration for your domain:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    location / {
        proxy_pass http://app:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring Setup

### 1. Prometheus Configuration
The default Prometheus configuration monitors:
- Application metrics
- Database performance
- System resources

### 2. Grafana Dashboards
Pre-configured dashboards include:
- Application performance metrics
- Database query performance
- System resource utilization
- Error rates and response times

### 3. Custom Metrics
Add custom metrics to your application:
```python
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Use in your routes
@app.route('/api/products')
@REQUEST_DURATION.time()
def get_products():
    REQUEST_COUNT.labels(method='GET', endpoint='/api/products').inc()
    # Your route logic here
```

## Scaling and Performance

### 1. Horizontal Scaling
Scale the application horizontally:
```bash
# Scale app service
docker-compose up -d --scale app=3

# Use load balancer
docker-compose up -d nginx
```

### 2. Database Optimization
For high-traffic applications:
- Enable connection pooling
- Configure read replicas
- Implement caching with Redis

### 3. Resource Limits
Set resource limits in docker-compose.yml:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

## Backup and Recovery

### 1. Database Backup
```bash
# Create backup
docker-compose exec postgres pg_dump -U inventory_user inventory_db > backup.sql

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U inventory_user inventory_db > "$BACKUP_DIR/backup_$DATE.sql"
```

### 2. Application Backup
```bash
# Backup application data
tar -czf app_backup_$(date +%Y%m%d).tar.gz \
  --exclude=venv \
  --exclude=__pycache__ \
  --exclude=*.pyc \
  .
```

### 3. Recovery Procedures
```bash
# Restore database
docker-compose exec -T postgres psql -U inventory_user inventory_db < backup.sql

# Restore application
tar -xzf app_backup_YYYYMMDD.tar.gz
```

## Security Considerations

### 1. Network Security
- Use internal Docker networks
- Expose only necessary ports
- Implement firewall rules

### 2. Access Control
- Use strong passwords
- Implement rate limiting
- Enable authentication for monitoring endpoints

### 3. Regular Updates
```bash
# Update base images
docker-compose pull
docker-compose up -d

# Security updates
docker-compose exec app pip install --upgrade --security
```

## Troubleshooting

### 1. Common Issues

#### Application Won't Start
```bash
# Check logs
docker-compose logs app

# Check database connection
docker-compose exec postgres psql -U inventory_user -d inventory_db -c "SELECT 1;"

# Verify environment variables
docker-compose exec app env | grep DB_
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U inventory_user

# Check connection pool
docker-compose exec postgres psql -U inventory_user -d inventory_db -c "SELECT * FROM pg_stat_activity;"
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Monitor database performance
docker-compose exec postgres psql -U inventory_user -d inventory_db -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

### 2. Log Analysis
```bash
# View all logs
docker-compose logs

# Follow specific service logs
docker-compose logs -f app

# Search logs for errors
docker-compose logs app | grep ERROR
```

## Maintenance

### 1. Regular Maintenance Tasks
- Monitor disk space usage
- Review and rotate logs
- Update dependencies
- Check security advisories

### 2. Health Checks
```bash
# Check service health
docker-compose ps

# Test application endpoints
curl -f http://localhost:5000/health

# Monitor metrics
curl http://localhost:5000/metrics
```

### 3. Performance Tuning
- Monitor slow queries
- Optimize database indexes
- Adjust connection pool settings
- Configure caching strategies

## Support and Resources

### 1. Documentation
- [API Documentation](README.md)
- [Configuration Guide](CONFIGURATION_README.md)
- [Coding Standards](CODING_STANDARDS.md)

### 2. Monitoring Tools
- Prometheus: Metrics collection
- Grafana: Visualization and alerting
- Docker: Container management
- Nginx: Reverse proxy and load balancing

### 3. Getting Help
- Check the troubleshooting section
- Review application logs
- Consult the API documentation
- Create an issue in the repository

## Conclusion
This deployment guide provides a comprehensive approach to deploying and maintaining the Inventory Management System in production. Follow the security best practices, monitor your application, and maintain regular backups to ensure a stable and secure deployment.
