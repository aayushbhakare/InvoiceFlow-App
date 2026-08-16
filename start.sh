#!/bin/bash

# Apply database migrations first
python manage.py migrate

# Start Celery worker with strict limits (1 process only) to save RAM
celery -A backend worker -l info --concurrency=1 --max-tasks-per-child=50 &

# Start Celery beat
celery -A backend beat -l info &

# Start Gunicorn with only 1 worker to save RAM
gunicorn backend.wsgi --bind 0.0.0.0:$PORT --workers 1 --threads 2