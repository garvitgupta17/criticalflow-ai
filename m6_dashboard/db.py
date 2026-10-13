
import os
import getpass

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Connect to the configured PostgreSQL database."""

    password = os.getenv("DB_PASSWORD")

    if not password:
        password = getpass.getpass("PostgreSQL password: ")

    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "criticalflow_ai"),
        user=os.getenv("DB_USER", "postgres"),
        password=password,
        connect_timeout=5,
    )


def load_incidents():
    """Fetch incidents from PostgreSQL as a Pandas DataFrame."""

    query = """
        SELECT *
        FROM incidents
        ORDER BY incident_id;
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = load_incidents()
    print("Total incidents:", len(df))
    print(df[["incident_id", "risk_label", "risk_score"]].to_string(index=False))
