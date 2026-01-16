FROM python:3.14-slim

# Temp for now, if needed will be uncomment
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY infra/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["uvicorn", "allocation.entrypoints.main:app", "--host", "0.0.0.0", "--port", "80"]
