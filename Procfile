web: gunicorn backend.wsgi --bind 0.0.0.0:$PORT
worker: celery -A backend worker -l info
beat: celery -A backend beat -l info
