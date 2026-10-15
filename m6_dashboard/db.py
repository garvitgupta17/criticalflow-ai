
import os

import pandas as pd
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


# --------------------------------------------------
# 1. Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# 2. Connect to Neon PostgreSQL
# --------------------------------------------------

def get_connection():
    """Connect securely to the Neon PostgreSQL database."""

    database_url = os.getenv("DASHBOARD_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DASHBOARD_DATABASE_URL is missing. "
            "Please check the .env file in your project root."
        )

    return psycopg.connect(
        database_url,
        sslmode="require",
        connect_timeout=10,
    )


# --------------------------------------------------
# 3. Load incidents from the database
# --------------------------------------------------

def load_incidents():
    """Fetch incident records into a Pandas DataFrame."""

    query = """
        SELECT *
        FROM incident_overview
        ORDER BY event_time DESC;
    """

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return pd.DataFrame(rows)


# --------------------------------------------------
# 4. Test connection and display a clean summary
# --------------------------------------------------

if __name__ == "__main__":

    try:
        df = load_incidents()

        print("\n" + "=" * 65)
        print("             NEON POSTGRESQL DASHBOARD")
        print("=" * 65)

        print("\nConnection Status : SUCCESS")
        print(f"Total Incidents   : {len(df):,}")
        print(f"Total Columns     : {len(df.columns)}")

        print("\nAvailable Columns:")
        for column in df.columns:
            print(f"  - {column}")

        if df.empty:
            print("\nNo incidents found in incident_overview.")

        else:
            preview_columns = [
                "incident_id",
                "event_type",
                "system",
                "job_name",
                "severity",
                "anomaly_score",
                "incident_status",
            ]

            available_columns = [
                column
                for column in preview_columns
                if column in df.columns
            ]

            print("\nRecent Incidents:")
            print("-" * 65)

            print(
                df[available_columns]
                .head(10)
                .to_string(index=False)
            )

        print("\n" + "=" * 65)
        print("Database test completed successfully.")
        print("=" * 65 + "\n")

    except Exception as error:
        print("\nDatabase connection or query failed.")
        print(f"Error: {error}")
