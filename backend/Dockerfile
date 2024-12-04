FROM python:3.12

WORKDIR /app/backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# For testing
# COPY .venv/lib/python3.12/site-packages/channels/testing/__init__.py /usr/local/lib/python3.12/site-packages/channels/testing/__init__.py

COPY . .
