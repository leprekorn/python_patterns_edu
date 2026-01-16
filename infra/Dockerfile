FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопируем код
COPY . .

# Настроим окружение
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Запустим через uvicorn
CMD ["uvicorn", "allocation.entrypoints.fastapi_app:app", "--host", "0.0.0.0", "--port", "80"]
