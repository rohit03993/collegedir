import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]


def database_url():
    load_dotenv(ROOT / ".env")
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and point it at a new empty database."
        )
    return url


def database_name():
    path = database_url().split("?", 1)[0].rsplit("/", 1)[-1]
    return path or "unknown"


def connect():
    return psycopg.connect(database_url(), row_factory=dict_row)
