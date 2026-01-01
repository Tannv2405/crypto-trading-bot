# Trading Bot Docker Management
.PHONY: help build up down logs shell config-shell db-shell clean restart status

# Default target
help:
	@echo "🤖 Trading Bot Docker Commands"
	@echo "================================"
	@echo "Development:"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start services (development mode)"
	@echo "  make down           - Stop services"
	@echo "  make restart        - Restart services"
	@echo "  make logs           - View logs"
	@echo "  make status         - Show service status"
	@echo ""
	@echo "Production:"
	@echo "  make prod-up        - Start services (production mode)"
	@echo "  make prod-down      - Stop production services"
	@echo "  make prod-logs      - View production logs"
	@echo ""
	@echo "Management:"
	@echo "  make shell          - Access trading bot shell"
	@echo "  make config-shell   - Access configuration CLI"
	@echo "  make db-shell       - Access database shell"
	@echo "  make pgadmin        - Start pgAdmin (admin interface)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          - Clean up containers and volumes"
	@echo "  make clean-all      - Clean everything including images"
	@echo "  make backup-db      - Backup database"
	@echo "  make restore-db     - Restore database"

# Development commands
build:
	@echo "🔨 Building Docker images..."
	docker-compose build

up:
	@echo "🚀 Starting services in development mode..."
	docker-compose up -d
	@echo "✅ Services started! Use 'make logs' to view output"

down:
	@echo "🛑 Stopping services..."
	docker-compose down

restart:
	@echo "🔄 Restarting services..."
	docker-compose restart

logs:
	@echo "📋 Viewing logs (Ctrl+C to exit)..."
	docker-compose logs -f

status:
	@echo "📊 Service Status:"
	docker-compose ps

# Production commands
prod-up:
	@echo "🚀 Starting services in production mode..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "✅ Production services started!"

prod-down:
	@echo "🛑 Stopping production services..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	@echo "📋 Viewing production logs..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Shell access
shell:
	@echo "🐚 Accessing trading bot shell..."
	docker-compose exec trading_bot /bin/bash

config-shell:
	@echo "⚙️ Starting configuration CLI..."
	docker-compose run --rm config_cli /bin/bash

db-shell:
	@echo "🗄️ Accessing database shell..."
	docker-compose exec postgres psql -U trading_user -d trading_bot

# Admin interface
pgadmin:
	@echo "🔧 Starting pgAdmin..."
	docker-compose --profile admin up -d pgadmin
	@echo "✅ pgAdmin started at http://localhost:8080"
	@echo "   Email: admin@trading-bot.local"
	@echo "   Password: admin123"

# Configuration management
config-list:
	@echo "📋 Listing configuration..."
	docker-compose run --rm config_cli python config_cli.py list

config-validate:
	@echo "✅ Validating configuration..."
	docker-compose run --rm config_cli python config_cli.py validate

config-export:
	@echo "💾 Exporting configuration..."
	docker-compose run --rm -v $(PWD):/backup config_cli python config_cli.py export /backup/config_backup.json

config-import:
	@echo "📥 Importing configuration..."
	docker-compose run --rm -v $(PWD):/backup config_cli python config_cli.py import /backup/config_backup.json

# Database management
backup-db:
	@echo "💾 Backing up database..."
	docker-compose exec postgres pg_dump -U trading_user -d trading_bot > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backed up to backup_$(shell date +%Y%m%d_%H%M%S).sql"

restore-db:
	@echo "📥 Restoring database..."
	@echo "⚠️  This will overwrite the current database!"
	@read -p "Enter backup file name: " backup_file; \
	docker-compose exec -T postgres psql -U trading_user -d trading_bot < $$backup_file

# Cleanup commands
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f

clean-all:
	@echo "🧹 Cleaning everything (containers, volumes, images)..."
	docker-compose down -v --rmi all
	docker system prune -af

# Health checks
health:
	@echo "🏥 Checking service health..."
	@echo "Database:"
	@docker-compose exec postgres pg_isready -U trading_user -d trading_bot || echo "❌ Database not ready"
	@echo "Trading Bot:"
	@docker-compose exec trading_bot python -c "from config.db_config import test_connection; print('✅ Bot healthy' if test_connection() else '❌ Bot unhealthy')" || echo "❌ Bot not running"

# Development helpers
dev-setup:
	@echo "🛠️ Setting up development environment..."
	cp .env.example .env
	@echo "✅ Created .env file - please edit with your configuration"
	@echo "📝 Next steps:"
	@echo "   1. Edit .env file with your API keys"
	@echo "   2. Run 'make build' to build images"
	@echo "   3. Run 'make up' to start services"

# Quick start
quick-start: dev-setup build up
	@echo "🎉 Quick start complete!"
	@echo "📊 View logs: make logs"
	@echo "⚙️ Manage config: make config-list"
	@echo "🔧 Admin panel: make pgadmin"