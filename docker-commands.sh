#!/bin/bash

# Docker commands for Financial Assistant API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << EOF
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Database URL (for local development)
DATABASE_URL=postgresql://financial_user:financial_password@localhost:5432/financial_db
EOF
    print_status "Created .env template. Please update with your actual values."
fi

# Function to build and run with docker-compose
run_with_compose() {
    print_status "Building and starting services with docker-compose..."
    docker-compose up --build -d
    print_status "Services started! API available at http://localhost:8000"
    print_status "Database available at localhost:5432"
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
    print_status "Services stopped."
}

# Function to view logs
view_logs() {
    print_status "Showing logs..."
    docker-compose logs -f
}

# Function to rebuild and restart
rebuild() {
    print_status "Rebuilding and restarting services..."
    docker-compose down
    docker-compose up --build -d
    print_status "Services rebuilt and restarted!"
}

# Function to run tests
run_tests() {
    print_status "Running tests in container..."
    docker-compose exec api python -m pytest
}

# Function to access database
db_shell() {
    print_status "Opening PostgreSQL shell..."
    docker-compose exec postgres psql -U financial_user -d financial_db
}

# Function to show status
show_status() {
    print_status "Service status:"
    docker-compose ps
}

# Function to clean up
cleanup() {
    print_warning "This will remove all containers, networks, and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Cleaning up..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_status "Cleanup complete!"
    else
        print_status "Cleanup cancelled."
    fi
}

# Main script logic
case "${1:-help}" in
    "start"|"up")
        run_with_compose
        ;;
    "stop"|"down")
        stop_services
        ;;
    "logs")
        view_logs
        ;;
    "rebuild")
        rebuild
        ;;
    "test")
        run_tests
        ;;
    "db")
        db_shell
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup
        ;;
    "help"|*)
        echo "Financial Assistant Docker Commands"
        echo "=================================="
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start, up     - Build and start services"
        echo "  stop, down    - Stop services"
        echo "  logs          - View logs"
        echo "  rebuild       - Rebuild and restart services"
        echo "  test          - Run tests"
        echo "  db            - Open PostgreSQL shell"
        echo "  status        - Show service status"
        echo "  cleanup       - Remove all containers and volumes"
        echo "  help          - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 start      # Start the application"
        echo "  $0 logs       # View logs"
        echo "  $0 db         # Access database"
        ;;
esac 