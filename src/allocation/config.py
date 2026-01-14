import os


def get_db_uri():
    host = os.environ.get("DB_HOST", "localhost")
    port = 15432 if host == "localhost" else 5432
    password = os.environ.get("DB_PASSWORD")
    user, db_name = "allocation", "allocation"
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url():
    host = os.environ.get("API_HOST", "localhost")
    port = 8000 if host == "localhost" else 80
    return f"http://{host}:{port}"
