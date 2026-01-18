import os
import dotenv
import pathlib


def get_db_uri():
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", 17432)
    password = os.environ.get("DB_PASSWORD")
    user = os.environ.get("DB_USER", "allocation")
    db_name = os.environ.get("DB_NAME", "allocation")
    if not password:
        pg_env_file = pathlib.Path(__file__).parent.parent.parent / "env" / "allocation.env"
        dotenv.load_dotenv(dotenv_path=pg_env_file)
        password = os.environ.get("DB_PASSWORD")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url():
    host = os.environ.get("API_HOST", "localhost")
    port = 8000 if host == "localhost" else 80
    return f"http://{host}:{port}"
