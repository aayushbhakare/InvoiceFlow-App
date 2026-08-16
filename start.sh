#!/bin/bash
set -e

echo "=== Running database migrations ==="
python manage.py migrate --verbosity 2
echo "=== Migrations completed successfully ==="

# Start Celery worker with strict limits (1 process only) to save RAM
celery -A backend worker -l info --concurrency=1 --max-tasks-per-child=50 &

# Start Celery beat
celery -A backend beat -l info &

# Start Gunicorn with only 1 worker to save RAM
gunicorn backend.wsgi --bind 0.0.0.0:$PORT --workers 1 --threads 2