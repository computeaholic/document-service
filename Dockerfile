FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN adduser --disabled-password appuser

COPY pyproject.toml .

COPY src ./src

RUN pip install --upgrade pip
RUN pip install .

USER appuser

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
