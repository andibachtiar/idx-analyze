import glob
import json
import logging
import os
import re
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

# Resolve the repository root independently of the current working directory.
PYTHON_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PYTHON_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE, override=False)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("idx_data_import.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# PostgreSQL Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

PG_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "postgres"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}

# Database and table name
DB_NAME = PG_CONFIG["database"]
TABLE_NAME = "financial_ratios"

def create_connection():
    """Create a SQLAlchemy PostgreSQL engine from the loaded environment."""
    try:
        if DATABASE_URL:
            connection_url = DATABASE_URL
            # Do not log the URL because it may contain a password.
            logger.info("Using DATABASE_URL from %s", ENV_FILE)
        else:
            if not PG_CONFIG["password"]:
                raise RuntimeError(
                    "Database credentials are missing. Set DATABASE_URL or "
                    "POSTGRES_PASSWORD in the project .env file."
                )
            connection_url = URL.create(
                drivername="postgresql+psycopg2",
                username=PG_CONFIG["user"],
                password=PG_CONFIG["password"],
                host=PG_CONFIG["host"],
                port=PG_CONFIG["port"],
                database=PG_CONFIG["database"],
            )
            logger.info(
                "Using POSTGRES_* configuration from %s (%s@%s:%s/%s)",
                ENV_FILE,
                PG_CONFIG["user"],
                PG_CONFIG["host"],
                PG_CONFIG["port"],
                PG_CONFIG["database"],
            )

        engine = create_engine(connection_url, pool_pre_ping=True)
        # Verify credentials immediately instead of waiting for to_sql().
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        logger.info("Database connection established")
        return engine
    except Exception as e:
        logger.error("Error connecting to PostgreSQL: %s", e)
        raise

def process_json_files(data_directory=None):
    """Process financial JSON files from the repository data directory."""
    data_directory = Path(data_directory) if data_directory else PROJECT_ROOT / "data"
    try:
        json_files = sorted(data_directory.glob("financial_*.json"))
        logger.info("Found %d JSON files to process", len(json_files))

        all_data = []

        # Process each file
        for file_path in json_files:
            logger.info("Processing %s", file_path)
            with file_path.open("r", encoding="utf-8") as file:
                try:
                    json_data = json.load(file)
                    if 'data' in json_data and json_data['data']:
                        all_data.extend(json_data['data'])
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON in {file_path}")
                    continue

        return all_data
    except Exception as e:
        logger.error(f"Error processing JSON files: {e}")
        raise

def to_snake_case(name):
    import re
    name = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def transform_data_to_dataframe(data):
    """Transform the raw data into a pandas DataFrame"""
    if not data:
        logger.warning("No data to transform")
        return pd.DataFrame()

    # Extract the data into a DataFrame
    try:
        df = pd.json_normalize(data)

        # Rename columns if they exist in the DataFrame
        df.columns = [to_snake_case(col) for col in df.columns]

        # Convert date columns to datetime
        if 'period_date' in df.columns:
            df['period_date'] = pd.to_datetime(df['period_date'])

        # Store the original raw data as JSON string
        # df['raw_data'] = data

        logger.info(f"Transformed data into DataFrame with {len(df)} rows and {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Error transforming data to DataFrame: {e}")
        raise

def load_data_to_postgres(df, engine):
    """Load DataFrame to PostgreSQL database"""
    if df.empty:
        logger.warning("No data to load into PostgreSQL")
        return

    try:
        # Load data to PostgreSQL
        df.to_sql(
            name=TABLE_NAME,
            con=engine,
            if_exists='append',
            index=False,
            chunksize=1000,
            method='multi'
        )
        logger.info(f"Successfully loaded {len(df)} rows into {TABLE_NAME}")
    except Exception as e:
        logger.error(f"Error loading data to PostgreSQL: {e}")
        raise

def main():
    """Run the financial-ratio ETL process."""
    logger.info("Starting ETL process")
    engine = create_connection()
    data = process_json_files()
    df = transform_data_to_dataframe(data)
    if not df.empty:
        load_data_to_postgres(df, engine)
    logger.info("ETL process completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("ETL process failed")
        raise
