FROM python:3.10-slim

WORKDIR /app

COPY poetry.lock pyproject.toml ./

RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction -vvv

COPY src/ ./
