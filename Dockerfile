FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências antes do código para aproveitar o cache de camadas
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install .

RUN mkdir -p data

EXPOSE 3005

CMD ["python", "-m", "app.main"]
