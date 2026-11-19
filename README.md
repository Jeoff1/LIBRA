# LIBRA

A Django 5.2 project backed by MySQL.

## Requirements

- Python 3.14
- MySQL 8.0.11+ or MariaDB 10.5+

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then fill in DJANGO_SECRET_KEY and DB_* values
```

Create the database (utf8mb4):

```sql
CREATE DATABASE libra_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Layout

- `config/` – settings, root URLs, WSGI/ASGI
- `apps/` – project apps (`apps.core` to start)
- `templates/`, `static/`, `media/`

## Checks

```bash
ruff check .
ruff format --check .
python manage.py check
python manage.py test
```
