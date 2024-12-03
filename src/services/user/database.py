import psycopg2
import psycopg2.extras
import os
from werkzeug import exceptions
from models import User

max_db_connect_retries = 10

def read_secret(secret_name):
    with open(f"/var/secrets/{secret_name}.txt", "r") as f:
        return f.readline()

# table: users
# columns: username, password_hashed, email, role

# to run locally, run docker compose up -d

def connect():
    #TODO_HC
    if os.getenv("KUBERNETES_MODE") == "in-cluster":
        conn = psycopg2.connect(
            host="localhost",
            port="5433",
            database="yugabyte",
            user="yugabyte", 
            password="yugabyte",
            connect_timeout=10,
        )
        # conn = psycopg2.connect(
        #     host=read_secret("DB_HOST"),
        #     port="5433",
        #     database="yugabyte",
        #     user=read_secret("DB_USER"),
        #     password=read_secret("DB_PW"),
        #     sslmode="verify-full",
        #     sslrootcert="/var/secrets/db.crt",
        #     connect_timeout=10,
        # )
    else:
        conn = psycopg2.connect(
            host="localhost",
            port="5433",
            database="yugabyte",
            user="yugabyte", 
            password="yugabyte",
            connect_timeout=10,
        )
    return conn

def insert_user(user):
    """insert user into database"""
    conn = connect()
    cursor = conn.cursor()
    try:
        # proceed with insertion
        cursor.execute(
            "INSERT INTO users (username, password_hashed, email, role) VALUES (%s, %s, %s, %s);",
            (
                user.username,
                user.password_hashed,
                user.email,
                user.role,
            ),
        )
    except psycopg2.Error as e:
        raise exceptions.BadRequest(description=f"Database error: {e}")
    finally:
        conn.commit()
        conn.close()

def get_user(username):
    """get user"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    row = cursor.fetchone()
    user = User(*row) if row is not None else None
    conn.close()
    return user

def remove_user(username):
    """delete user from username"""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE username = %s;", (username,))
    conn.commit()
    conn.close()

def update_user(username, password_hashed, email, role):
    """update values of user with given username"""
    conn = connect()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """UPDATE users SET
                password_hashed = %s,
                email = %s,
                role = %s
                WHERE username = %s;""",
            (
                password_hashed,
                email,
                role,
                username,
            ),
        )
    except psycopg2.Error as e:
        raise exceptions.BadRequest(description=f"Database error: {e}")
    finally:
        conn.commit()
        conn.close()

def read_users() -> [User]:
    """Reads all users from the users table"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users;")

    rows = cursor.fetchall()

    # Parse challenges
    users = [User(*row) for row in rows]

    conn.close()

    return users