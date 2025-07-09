# Montal Home

## Description
A Django web application for managing a furniture store with improved architecture, class-based views, and better development workflow.

## Quick Start (Locally)

### 1. Clone the repository
```sh
git clone <repository-url>
cd Montal_Home
```

### 2. Install dependencies
It is recommended to use Python 3.11+ and a virtual environment:
```sh
make install
```

### 3. Set up environment variables
Create a `.env` file in the project root and add the following variables:
```
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
NOVA_POSHTA_API_KEY=your_novaposhta_key
```

### 4. Apply migrations and collect static files
```sh
make setupdb
```

### 5. Run the server
```sh
make run
```

## Running with Docker Compose

1. Make sure Docker and docker-compose are installed.
2. Create a `.env` file in the root (see above).
3. Run:
```sh
docker-compose up --build
```

- The app will be available at http://localhost:8000
- PgAdmin — http://localhost:5050 (email: admin@admin.com, password: admin)

## Development Commands

### Makefile Commands
- `make help` — show all available commands
- `make install` — install dependencies in virtual environment
- `make run` — start development server
- `make test` — run tests
- `make lint` — run code quality checks (isort, black, mypy)
- `make autofmt` — auto-format code
- `make clean` — clean up cache and temporary files
- `make migrate` — apply database migrations
- `make makemigrations` — create new migrations
- `make shell` — open Django shell
- `make collectstatic` — collect static files
- `make dev` — quick development setup (install + setupdb + run)

### Code Quality
```sh
make lint          # Run all code quality checks
make autofmt       # Auto-format code
make precommit     # Run pre-commit checks (format + lint + test)
```

### Database Operations
```sh
make makemigrations  # Create new migrations
make migrate         # Apply migrations
make setupdb         # Create and apply migrations
```

### Loading Data
```sh
# Load fixtures with custom command
python manage.py load_fixtures data.json

# Or use Django's built-in command
python manage.py loaddata data.json
```

## Project Structure Improvements

### 🔧 **Refactoring Highlights**

1. **Class-Based Views**: Converted function-based views to class-based views for better organization and reusability
2. **Improved Models**: Added validation, properties, and better field definitions
3. **Enhanced Settings**: Added security settings, logging, caching, and better environment configuration
4. **Better Development Workflow**: Improved Makefile with comprehensive commands
5. **Database Access Fix**: Moved parameter creation from app initialization to post_migrate signals
6. **Code Quality**: Organized requirements.txt and added comprehensive linting tools

### **Key Features**
- ✅ Class-based views for better maintainability
- ✅ Enhanced security settings for production
- ✅ Improved error handling and validation
- ✅ Better development workflow with Makefile
- ✅ Comprehensive code quality tools
- ✅ Custom management commands
- ✅ Ukrainian localization support
- ✅ PostgreSQL support for production

## Tests
```sh
make test
```

## Production Deployment
```sh
make production  # Clean, collect static, and migrate
```

---

If you have any questions, check the settings in `store/settings.py` and `docker-compose.yml`.