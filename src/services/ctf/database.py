import psycopg2
import psycopg2.extras
import psycopg2.sql as sql
import os
import json
from werkzeug import exceptions
from models import Challenge

max_db_connect_retries = 10

def read_secret(secret_name):
    with open(f"/var/secrets/{secret_name}.txt", "r") as f:
        return f.readline()

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

def insert_challenge(challenge: Challenge):
    """Inserts Challenge into db"""
    conn = connect()
    cursor = conn.cursor()

    try:
        # Check if challenge with given id already exists
        cursor.execute("SELECT id FROM challenges WHERE id = %s;", (challenge.id,))
        if cursor.fetchone() is not None:
            raise exceptions.Conflict(description=f"Challenge already exists.")

        # Check if Challenge with given name already exists
        cursor.execute("SELECT name FROM challenges WHERE name = %s;", (challenge.name,))
        if cursor.fetchone() is not None:
            print(challenge.name)
            raise exceptions.Conflict(
                description=f"Challenge with name {challenge.name} already exists."
            )

        # If neither id nor name exists, proceed with insertion
        cursor.execute(
            "INSERT INTO challenges (id, name, description, category, difficulty, flag_format, author, flag, resource_limits, score, testing, ready, image_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
            (
                challenge.id,
                challenge.name,
                challenge.description,
                challenge.category,
                challenge.difficulty,
                challenge.flag_format,
                challenge.author,
                challenge.flag,
                json.dumps(challenge.resource_limits),
                challenge.score,
                challenge.testing,
                challenge.ready,
                challenge.image_url,
            ),
        )
    except psycopg2.Error as e:
        raise exceptions.BadRequest(description=f"Database error: {e}")
    finally:
        conn.commit()
        conn.close()

def delete_all_challenges():
    """Deletes all challenges from the table"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM challenges;")
    conn.commit()
    conn.close()

def update_challenge(challenge: Challenge):
    """Updates challenge in db with given id"""
    conn = connect()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """UPDATE challenges SET
                name = %s,
                description = %s,
                category = %s,
                difficulty = %s,
                flag_format = %s,
                author = %s,
                flag = %s,
                resource_limits = %s,
                score = %s,
                testing = %s,
                ready = %s,
                image_url = %s,
                competition_id = %s
                WHERE id = %s;""",
            (
                challenge.name,
                challenge.description,
                challenge.category,
                challenge.difficulty,
                challenge.flag_format,
                challenge.author,
                challenge.flag,
                json.dumps(challenge.resource_limits),
                challenge.score,
                challenge.testing,
                challenge.ready,
                challenge.image_url,
                challenge.competition_id,
                challenge.id,
            ),
        )
    except psycopg2.Error as e:
        raise exceptions.BadRequest(description=f"Database error: {e}")
    finally:
        conn.commit()
        conn.close()

def patch_update_challenge(challenge_id, data):
    """Updates Challenge in db with given id"""
    conn = connect()
    cursor = conn.cursor()

    #Generate dynamic sql stmt
    query = sql.SQL("UPDATE challenges SET {data} WHERE id = {id};").format(
    data=sql.SQL(', ').join(
        sql.Composed([sql.Identifier(k), sql.SQL(" = "), sql.Placeholder(k)]) for k in data.keys()
    ),
    id=sql.Placeholder('id')
    )
    #adding the id to the dict for easily parsing.
    data["id"] = challenge_id

    try:
        cursor.execute(
            query,
            data,
        )
    except psycopg2.Error as e:
        raise exceptions.BadRequest(description=f"Database error: {e}")
    finally:
        conn.commit()
        conn.close()

def add_challenges_to_competition(challenges, competition_id) -> [Challenge]:
    """Add the challenges to the competition"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("UPDATE challenges set competition_id=%s WHERE id IN %s;", (competition_id, challenges,))

    #Retrieve competitions
    cursor.execute("select * from challenges where id in %s;", (challenges,))
    rows = cursor.fetchall()

    # Parse challenges
    updated_challenges = [Challenge(*row) for row in rows]

    conn.commit()
    conn.close()

    return updated_challenges

def read_challenges() -> [Challenge]:
    """Reads all challenges from the table"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM challenges;")

    rows = cursor.fetchall()

    # Parse challenges
    challenges = [Challenge(*row) for row in rows]

    conn.close()

    return challenges

def read_challenges_from_author(username) -> [Challenge]:
    """Reads all challenges from the table"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM challenges where author=%s;",(username,))

    rows = cursor.fetchall()

    # Parse challenges
    challenges = [Challenge(*row) for row in rows]

    conn.close()

    return challenges

def read_challenges_from_competitions(competition_ids) -> [Challenge]:
    """Returns all challenges with relationship to the given competition_id"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM challenges WHERE competition_id IN %s;", (competition_ids,))
    rows = cursor.fetchall()

    challenges = [Challenge(*row) for row in rows]

    conn.close()

    return challenges

def read_challenge(challenge_id) -> Challenge:
    """Returns Challenges with given id from db"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM challenges WHERE id = %s;", (challenge_id,))
    row = cursor.fetchone()

    challenge = Challenge(*row) if row is not None else None

    conn.close()

    if challenge is None:
        raise exceptions.NotFound()

    return challenge

def remove_challenge(challenge_id):
    """Removes Challenge with given id from db if it exists."""
    conn = connect()
    cursor = conn.cursor()

    # Check if Challenge exists
    cursor.execute("SELECT id FROM challenges WHERE id = %s;", (challenge_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise exceptions.NotFound(description="Challenge does not exist.")

    # Delete Challenge
    cursor.execute("DELETE FROM challenges WHERE id = %s;", (challenge_id,))
    conn.commit()
    conn.close()