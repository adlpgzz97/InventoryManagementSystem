#!/bin/bash

# Inventory Management System - Deployment Script
# This script automates the deployment process for different environments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT=${1:-development}
COMPOSE_FILE="docker-compose.yml"
COMPOSE_PROD_FILE="docker-compose.prod.yml"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    success "Prerequisites check passed"
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    mkdir -p "$PROJECT_DIR/backups"
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/uploads"
    mkdir -p "$PROJECT_DIR/secrets"
    mkdir -p "$PROJECT_DIR/monitoring/rules"
    mkdir -p "$PROJECT_DIR/monitoring/grafana/provisioning/dashboards"
    mkdir -p "$PROJECT_DIR/monitoring/grafana/provisioning/datasources"
    mkdir -p "$PROJECT_DIR/nginx/ssl"
    
    success "Directories created"
}

# Generate secrets
generate_secrets() {
    log "Generating secrets..."
    
    # Generate app secret key
    if [ ! -f "$PROJECT_DIR/secrets/app_secret_key.txt" ]; then
        openssl rand -base64 32 > "$PROJECT_DIR/secrets/app_secret_key.txt"
        log "Generated app secret key"
    fi
    
    # Generate database password
    if [ ! -f "$PROJECT_DIR/secrets/db_password.txt" ]; then
        openssl rand -base64 16 > "$PROJECT_DIR/secrets/db_password.txt"
        log "Generated database password"
    fi
    
    # Generate Redis password
    if [ ! -f "$PROJECT_DIR/secrets/redis_password.txt" ]; then
        openssl rand -base64 16 > "$PROJECT_DIR/secrets/redis_password.txt"
        log "Generated Redis password"
    fi
    
    # Generate Grafana password
    if [ ! -f "$PROJECT_DIR/secrets/grafana_password.txt" ]; then
        openssl rand -base64 16 > "$PROJECT_DIR/secrets/grafana_password.txt"
        log "Generated Grafana password"
    fi
    
    success "Secrets generated"
}

# Set proper permissions
set_permissions() {
    log "Setting proper permissions..."
    
    chmod 600 "$PROJECT_DIR/secrets"/*
    chmod 755 "$PROJECT_DIR/scripts"/*
    
    success "Permissions set"
}

# Create environment file
create_env_file() {
    log "Creating environment file..."
    
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        
        # Update with generated secrets
        DB_PASSWORD=$(cat "$PROJECT_DIR/secrets/db_password.txt")
        REDIS_PASSWORD=$(cat "$PROJECT_DIR/secrets/redis_password.txt")
        APP_SECRET_KEY=$(cat "$PROJECT_DIR/secrets/app_secret_key.txt")
        
        # Update .env file
        sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD/" "$PROJECT_DIR/.env"
        sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASSWORD/" "$PROJECT_DIR/.env"
        sed -i "s/SECRET_KEY=.*/SECRET_KEY=$APP_SECRET_KEY/" "$PROJECT_DIR/.env"
        
        success "Environment file created and configured"
    else
        warning "Environment file already exists, skipping creation"
    fi
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" build --no-cache
    else
        docker-compose -f "$COMPOSE_FILE" build --no-cache
    fi
    
    success "Docker images built"
}

# Start services
start_services() {
    log "Starting services..."
    
    cd "$PROJECT_DIR"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f "$COMPOSE_FILE" -f "$COMPOSE_PROD_FILE" up -d
    else
        docker-compose -f "$COMPOSE_FILE" up -d
    fi
    
    success "Services started"
}

# Wait for services to be ready
wait_for_services() {
    log "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    log "Waiting for PostgreSQL..."
    until docker-compose exec -T postgres pg_isready -U inventory_user -d inventory_db; do
        sleep 2
    done
    success "PostgreSQL is ready"
    
    # Wait for Redis
    log "Waiting for Redis..."
    until docker-compose exec -T redis redis-cli ping; do
        sleep 2
    done
    success "Redis is ready"
    
    # Wait for application
    log "Waiting for application..."
    until curl -f http://localhost:5000/health &> /dev/null; do
        sleep 5
    done
    success "Application is ready"
    
    # Wait for Prometheus
    log "Waiting for Prometheus..."
    until curl -f http://localhost:9090/-/healthy &> /dev/null; do
        sleep 5
    done
    success "Prometheus is ready"
    
    # Wait for Grafana
    log "Waiting for Grafana..."
    until curl -f http://localhost:3000/api/health &> /dev/null; do
        sleep 5
    done
    success "Grafana is ready"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd "$PROJECT_DIR"
    
    # Wait a bit more for database to be fully ready
    sleep 10
    
    # Run migrations if they exist
    if [ -f "$PROJECT_DIR/backend/utils/migrations/migrate.py" ]; then
        docker-compose exec -T app python -m backend.utils.migrations.migrate
        success "Database migrations completed"
    else
        warning "No migration script found, skipping migrations"
    fi
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check all services
    cd "$PROJECT_DIR"
    
    if docker-compose ps | grep -q "Up"; then
        success "All services are running"
        
        # Display service status
        log "Service status:"
        docker-compose ps
        
        # Display URLs
        log "Service URLs:"
        echo "  - Application: http://localhost:5000"
        echo "  - Grafana: http://localhost:3000 (admin/$(cat secrets/grafana_password.txt))"
        echo "  - Prometheus: http://localhost:9090"
        
    else
        error "Some services are not running properly"
        docker-compose ps
        exit 1
    fi
}

# Backup existing data (if any)
backup_existing() {
    log "Checking for existing data..."
    
    cd "$PROJECT_DIR"
    
    if docker-compose ps | grep -q "Up"; then
        warning "Existing services detected. Creating backup..."
        
        # Create backup directory with timestamp
        BACKUP_DIR="$PROJECT_DIR/backups/backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup database
        if docker-compose exec -T postgres pg_isready -U inventory_user -d inventory_db &> /dev/null; then
            docker-compose exec -T postgres pg_dump -U inventory_user inventory_db > "$BACKUP_DIR/database_backup.sql"
            log "Database backup created: $BACKUP_DIR/database_backup.sql"
        fi
        
        # Backup application data
        tar -czf "$BACKUP_DIR/app_data_backup.tar.gz" \
            --exclude=venv \
            --exclude=__pycache__ \
            --exclude=*.pyc \
            --exclude=backups \
            --exclude=logs \
            . 2>/dev/null || true
        
        log "Application data backup created: $BACKUP_DIR/app_data_backup.tar.gz"
        
        success "Backup completed"
    fi
}

# Stop existing services
stop_existing() {
    log "Stopping existing services..."
    
    cd "$PROJECT_DIR"
    
    if docker-compose ps | grep -q "Up"; then
        docker-compose down
        success "Existing services stopped"
    fi
}

# Clean up (optional)
cleanup() {
    if [ "$2" = "--cleanup" ]; then
        log "Cleaning up unused Docker resources..."
        
        # Remove unused containers
        docker container prune -f
        
        # Remove unused images
        docker image prune -f
        
        # Remove unused volumes
        docker volume prune -f
        
        # Remove unused networks
        docker network prune -f
        
        success "Cleanup completed"
    fi
}

# Main deployment function
deploy() {
    log "Starting deployment for environment: $ENVIRONMENT"
    
    # Check prerequisites
    check_prerequisites
    
    # Create directories
    create_directories
    
    # Generate secrets
    generate_secrets
    
    # Set permissions
    set_permissions
    
    # Create environment file
    create_env_file
    
    # Backup existing data
    backup_existing
    
    # Stop existing services
    stop_existing
    
    # Build images
    build_images
    
    # Start services
    start_services
    
    # Wait for services
    wait_for_services
    
    # Run migrations
    run_migrations
    
    # Health check
    health_check
    
    success "Deployment completed successfully!"
    
    # Cleanup if requested
    cleanup "$@"
}

# Show usage
usage() {
    echo "Usage: $0 [environment] [options]"
    echo ""
    echo "Environments:"
    echo "  development  - Deploy development environment (default)"
    echo "  production   - Deploy production environment"
    echo ""
    echo "Options:"
    echo "  --cleanup    - Clean up unused Docker resources after deployment"
    echo "  --help       - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy development environment"
    echo "  $0 production         # Deploy production environment"
    echo "  $0 production --cleanup  # Deploy production and cleanup"
}

# Main script logic
case "${1:-}" in
    --help|-h)
        usage
        exit 0
        ;;
    production|development)
        deploy "$@"
        ;;
    *)
        if [ -n "$1" ]; then
            error "Unknown environment: $1"
            usage
            exit 1
        else
            deploy "$@"
        fi
        ;;
esac
