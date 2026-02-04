# python_patterns_edu
Education by book Persival - Python patterns https://www.cosmicpython.com/


# Install env:
```
poetry install --all-groups
```


# Build process:
Export requirements.txt
```
poetry export -f requirements.txt --output infra/requirements.txt
```

Build container:
```
docker build -f infra/Dockerfile -t leprekorn/allocation:0.0.1 .
```

Test build container:
```
docker run --rm  leprekorn/allocation:0.0.1 python -c "from allocation.entrypoints.main import app; print('OK')"
```


# Alembic database migrations:
```
alembic revision --autogenerate -m "Added field version to Product"
alembic upgrade head
```
