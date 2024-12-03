from models import Competition
import uuid
import psycopg2
import psycopg2.extras
import psycopg2.sql as sql
from werkzeug import exceptions
import os

def read_secret(secret_name):
    with open(f"/var/secrets/{secret_name}.txt", "r") as f:
        return f.readline()

def connect():
    if os.getenv("KUBERNETES_MODE") == "in-cluster":
        conn = psycopg2.connect(
            # Default to Yugabyte defaults
            host="localhost",
            port=os.getenv("DB_PORT", "5433"),
            database=os.getenv("DB_NAME", "yugabyte"),
            user=os.getenv("DB_USER", "yugabyte"),
            password=os.getenv("DB_PW", "yugabyte"),
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
        #TODO_HC
        conn = psycopg2.connect(
            # Default to Yugabyte defaults
            host="localhost",
            port=os.getenv("DB_PORT", "5433"),
            database=os.getenv("DB_NAME", "yugabyte"),
            user=os.getenv("DB_USER", "yugabyte"),
            password=os.getenv("DB_PW", "yugabyte"),
            connect_timeout=10,
        )
    return conn

def get_competitions():
    '''Returns all competitions'''
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, active FROM competitions;')
    rows = cursor.fetchall()
    conn.close()
    competitions = [Competition(id=row[0], name=row[1], active=row[2]) for row in rows] # Test af actions
    return competitions

def get_competition_by_id(competition_id: str):
    '''Return specific competition by id'''
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, active FROM competitions WHERE id = %s;', (competition_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Competition(id=row[0], name=row[1], active=row[2])
    else:
        return None

def get_competitions_active():
    '''Returns all competitions that are currently active'''
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, active FROM competitions WHERE active = True;')
    rows = cursor.fetchall()
    conn.close()
    competitions = [Competition(id=row[0], name=row[1], active=row[2]) for row in rows] 
    return competitions

def put_competition(competition: Competition):
    '''Inserts a new competition'''
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO competitions (name, active) 
        VALUES (%s, %s) RETURNING id;''', (competition.name, competition.active))
        competition.id = cursor.fetchone()[0] # get auto-generated ID
        conn.commit()
    except psycopg2.DatabaseError as e:
        raise exceptions.BadRequest(description=f"Error inserting competition: {e}")
    finally:
        conn.close()
    return competition

def update_competition(competition: Competition):
    '''Updates a competition with set id'''
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        UPDATE competitions
        SET name = %s, active = %s
        WHERE id = %s;''',
        (competition.name, competition.active, competition.id))
        conn.commit()
    except psycopg2.DatabaseError as e:
        raise exceptions.BadRequest(description=f"Database error occurred: {e}") 
    finally:
        conn.close()
    return competition


'''Competitions participants'''
def put_competition_user(username: str, competition_id: str):
    '''Inserts a user into a competition'''
    conn = connect()
    cursor = conn.cursor()
    try:
        # Check if the participant already exists
        cursor.execute('SELECT COUNT(*) FROM participants WHERE username = %s AND competition_id = %s;',
                       (username, competition_id))
        if cursor.fetchone()[0] > 0:
            raise exceptions.BadRequest(description="Participant already exists in this competition.")

        # Insert the participant
        cursor.execute('''
        INSERT INTO participants (username, competition_id) 
        VALUES (%s, %s);''', (username, competition_id))
        conn.commit()
    except psycopg2.DatabaseError as e:
        raise exceptions.BadRequest(description=f"Error inserting participant: {e}") 
    finally:
        conn.close()
    participants = {'username': username, 'competition_id': competition_id}
    return participants

def get_competitions_users():
    '''Returns all competitions and their participants'''
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT competition_id, username FROM participants;')
    rows = cursor.fetchall()
    conn.close()
    participants = [{'competition_id': row[0], 'username': row[1]} for row in rows]
    return participants

def get_competition_users(competition_id: str):
    '''Return all users in a competition'''
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM participants WHERE competition_id = %s;', (competition_id,))
    rows = cursor.fetchall()
    conn.close()
    participants =  [{'competition_id': competition_id, 'username': row[0]} for row in rows]
    return participants

def get_user_competitions(username:str):
    '''Returns all competition a specific user participates in'''
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT username FROM participants WHERE username = %s;', (username,))
    rows = cursor.fetchall()
    conn.close()
    participants =  [{'competition_id': row[0], 'username': username} for row in rows]
    return participants

'''Leaderboard'''
def get_leaderboard():
    """Rank users based on their cumulative score across all competitions."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    with rankedscore AS
  (SELECT username, score, competition_id, challenge_id, valid, ROW_NUMBER() OVER (PARTITION BY username, competition_id, challenge_id ORDER BY timestamp DESC) AS rn
  FROM submissions)

  select username, sum(score) from rankedscore
  where rn=1
  group by username
    """)
    rows = cursor.fetchall()
    conn.close()
    scores =  [{'username': row[0], 'score': row[1]} for row in rows]
    return scores

def get_competition_leaderboard(competition_id):
    """Rank users based on their total score within a specific competition."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    with rankedscore AS
  (SELECT username, score, competition_id, challenge_id, valid, ROW_NUMBER() OVER (PARTITION BY username, competition_id, challenge_id ORDER BY timestamp DESC) AS rn
  FROM submissions)

  select username, sum(score) from rankedscore
  where rn=1 and competition_id = %s
  group by username
    """, (competition_id,))
    rows = cursor.fetchall()
    conn.close()
    scores =  [{'username': row[0], 'score': row[1]} for row in rows]
    return scores

def get_challenge_leaderboard(challenge_id):
    """Rank users based on their score within a specific challenge."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
    with rankedscore AS
  (SELECT username, score, competition_id, challenge_id, valid, ROW_NUMBER() OVER (PARTITION BY username, competition_id, challenge_id ORDER BY timestamp DESC) AS rn
  FROM submissions)

  select username, sum(score) from rankedscore
  where rn=1 and challenge_id = %s
  group by username
    """, (challenge_id,))    
    rows = cursor.fetchall()
    conn.close()
    scores =  [{'username': row[0], 'score': row[1]} for row in rows]
    return scores

def delete_submissions():
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM submissions;")
        conn.commit()
        message = "All submissions deleted successfully."
    except psycopg2.DatabaseError as e:
        raise exceptions.BadRequest(description=f"Database error occurred: {e}")
    finally:
        conn.close()
    return message

def delete_submissions_where(data):
    """Reset the leaderboard by clearing submissions based on data filters."""
    query = sql.SQL("DELETE FROM submissions WHERE {data};").format(
    data=sql.SQL(', ').join(
        sql.Composed([sql.Identifier(k), sql.SQL(" = "), sql.Placeholder(k)]) for k in data.keys()
    ))

    conn = connect()
    cursor = conn.cursor()

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
    return f"All submissions with given filters {data} deleted successfully."

def put_submission(username: str, competition_id: str, challenge_id: str, submission_flag: str, score: int, admin: bool, valid: bool):
    """Inserts a log of the user's submission of flag"""
    conn = connect()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO submissions (username, competition_id, challenge_id, submission_flag, score, admin, valid) 
        VALUES (%s, %s, %s, %s, %s, %s, %s);''', (username, competition_id, challenge_id, submission_flag, score, admin, valid))
        conn.commit()
    except psycopg2.DatabaseError as e:
        raise exceptions.BadRequest(description=f"Error inserting submissions: {e}") 
    finally:
        conn.close()
    submission = {'username': username, 'competition_id': competition_id, 'challenge_id': challenge_id, 'submission_flag': submission_flag, 'score': score, 'admin': admin, 'valid': valid}
    return submission

def get_submissions():
    '''Return all submissions'''
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM submissions')
    rows = cursor.fetchall()
    conn.close()
    #TODO fix this toxic shit xdd
    submissions =  [{'id': row[0],'username': row[1], 'competition_id': row[2], 'challenge_id': row[3], 'timestamp': row[4], 'submission_flag': row[5], 'score': row[6], 'admin': row[7], 'valid': row[8]} for row in rows]
    return submissions

def get_submissions_challenge_user(challenge_id, username):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM submissions WHERE username = %s AND challenge_id = %s;', (username, challenge_id, ))
    rows = cursor.fetchall()
    conn.close()
    submissions =  [{'id': row[0],'username': row[1], 'competition_id': row[2], 'challenge_id': row[3], 'timestamp': row[4], 'submission_flag': row[5], 'score': row[6], 'admin': row[7], 'valid': row[8]} for row in rows]
    return submissions