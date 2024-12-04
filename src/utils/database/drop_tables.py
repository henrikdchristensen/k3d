import psycopg2
import psycopg2.extras
from config import DB_CONFIG

# Drop table queries (reverse order of dependencies)
DROP_TABLE_QUERIES = [
    "DROP TABLE IF EXISTS submissions;",
    "DROP TABLE IF EXISTS participants;",
    "DROP TABLE IF EXISTS challenges;",
    "DROP TABLE IF EXISTS competitions;",
    "DROP TABLE IF EXISTS users;",
]

def drop_tables():
    """Drop existing tables."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    try:
        for query in DROP_TABLE_QUERIES:
            cursor.execute(query)
            print(f"Dropped table: {query.strip()}")
        conn.commit()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    drop_tables()
