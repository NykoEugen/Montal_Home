# Montal Home

## Description
A Django web application for managing a furniture store.

## Quick Start (Locally)

### 1. Clone the repository
```sh
git clone <repository-url>
cd Montal_Home
```

### 2. Install dependencies
It is recommended to use Python 3.11+ and a virtual environment:
```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
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
python manage.py migrate
python manage.py collectstatic --noinput
```

### 5. Run the server
```sh
python manage.py runserver
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


## Makefile commands
- `make run` — start the development server
- `make test` — run tests
- `make lint` — code check (isort, black, mypy)
- `make autofmt` — auto-format code


## Tests
```sh
make test
```