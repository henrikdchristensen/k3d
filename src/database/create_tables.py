import psycopg2
import psycopg2.extras
from psycopg2 import OperationalError
import time
from config import DB_CONFIG

# Create table queries (dependencies respected)
CREATE_TABLE_QUERIES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        username VARCHAR(255) PRIMARY KEY,
        password_hashed VARCHAR(255),
        email VARCHAR(255),
        role VARCHAR(255)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS competitions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name TEXT NOT NULL,
        active BOOLEAN NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS participants (
        username VARCHAR(255) NOT NULL,
        competition_id UUID NOT NULL,
        PRIMARY KEY (username, competition_id),
        FOREIGN KEY (competition_id)
            REFERENCES competitions (id)
            ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS challenges (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) UNIQUE,
        description VARCHAR(255),
        category VARCHAR(255),
        difficulty VARCHAR(255),
        flag_format VARCHAR(255),
        author VARCHAR(255),
        flag VARCHAR(255),
        resource_limits VARCHAR(255),
        score INTEGER,
        testing BOOLEAN,
        ready BOOLEAN,
        image_url VARCHAR(255),
        competition_id UUID,
        CONSTRAINT fk_competition_id FOREIGN KEY (competition_id)
            REFERENCES competitions (id)
            ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS submissions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        username VARCHAR(255) NOT NULL,
        competition_id UUID NOT NULL,
        challenge_id UUID NOT NULL,
        timestamp TIMESTAMP DEFAULT now(),
        submission_flag VARCHAR(255),
        score INTEGER NOT NULL,
        admin BOOLEAN NOT NULL,
        valid BOOLEAN NOT NULL,
        FOREIGN KEY (username, competition_id)
            REFERENCES participants (username, competition_id)
            ON DELETE CASCADE
    );
    """
]

def create_tables():
    """Create tables with retry logic."""
    retries = 5
    delay = 5  # seconds

    while retries > 0:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            try:
                cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
                for query in CREATE_TABLE_QUERIES:
                    cursor.execute(query)
                    print(f"Created table: {query.strip()[:50]}...")  # Print first 50 chars of query
                conn.commit()
                print("All tables created successfully.")
                break  # Exit the loop if successful
            finally:
                cursor.close()
                conn.close()
        except OperationalError as e:
            retries -= 1
            print(f"Failed to connect to the database. Retries left: {retries}")
            print(f"Error: {e}")
            if retries == 0:
                print("Max retries reached. Exiting.")
                raise
            time.sleep(delay)  # Wait before retrying

if __name__ == "__main__":
    create_tables()
