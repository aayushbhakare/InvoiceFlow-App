#!/bin/bash
# Start Celery worker in the background
celery -A backend worker -l info &

# Start Celery beat in the background
celery -A backend beat -l info &

# Apply database migrations
python manage.py migrate

# Start Gunicorn
gunicorn backend.wsgi --bind 0.0.0.0:$PORT
