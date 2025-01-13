#!/bin/bash

python manage.py migrate
uvicorn copygram.asgi:application --host 0.0.0.0 --port 8000 --reload
