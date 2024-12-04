#!/bin/bash

python manage.py migrate
python manage.py collectstatic --no-input

gunicorn -k uvicorn.workers.UvicornWorker copygram.asgi:application --bind 0.0.0.0:8000